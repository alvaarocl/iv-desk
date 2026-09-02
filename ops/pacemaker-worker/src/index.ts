// Cloud pacemaker: dispatches the IV Desk loop workflow every 15 min via Cloudflare Cron
// Triggers, independent of any laptop or local Claude Code session staying alive.
//
// Deliberately sends NO `inputs.mode` — a bare workflow_dispatch inherits the DESK_MODE repo
// variable (agent/.github/workflows/desk.yml's `inherit` fix), which is what keeps
// `gh variable set DESK_MODE --body exits_only` working as a real kill switch. Hard-coding a
// mode here would re-arm it every 15 minutes and silently defeat that — see
// ops/pacemaker.sh's own comment for the same reasoning; this worker exists to replace THAT
// script, not to reintroduce the trap it was built to avoid.

export interface Env {
  GH_TOKEN: string;
}

const REPO = "alvaarocl/iv-desk";
const WORKFLOW = "desk.yml";

export default {
  async scheduled(_event: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(dispatch(env));
  },

  // GET so a human (or an uptime check) can trigger a manual tick / sanity-check the token
  // without waiting for the next cron slot. Not authenticated beyond the worker's own URL
  // being unguessable-ish; the real access control is the GH_TOKEN, which never leaves the
  // Authorization header sent to GitHub.
  async fetch(_req: Request, env: Env): Promise<Response> {
    const result = await dispatch(env);
    return new Response(result, { status: result.startsWith("ok") ? 200 : 500 });
  },
};

async function dispatch(env: Env): Promise<string> {
  const resp = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GH_TOKEN}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "iv-desk-pacemaker-worker",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: "main" }),
    },
  );
  const stamp = new Date().toISOString();
  if (resp.status === 204) {
    console.log(`${stamp} ok: dispatched`);
    return `ok: dispatched at ${stamp}`;
  }
  const body = await resp.text();
  console.error(`${stamp} FAILED ${resp.status}: ${body}`);
  return `FAILED ${resp.status} at ${stamp}: ${body}`;
}
