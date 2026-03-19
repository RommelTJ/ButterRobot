---
name: gitlab
description: Fetch, review, and comment on GitLab merge requests. Check pipeline status.
metadata: {"openclaw":{"requires":{"env":["GITLAB_URL","GITLAB_TOKEN"]}}}
---

# GitLab MR Skill

Interact with GitLab merge requests and pipelines via the API. All commands run on the miniPC using the exec tool.

## Authentication

Every request uses these environment variables (already configured on the miniPC):

- `$GITLAB_URL` — base URL (e.g. `https://gitlab.example.com`)
- `$GITLAB_TOKEN` — Personal Access Token

Header for all curl calls:

```
-H "PRIVATE-TOKEN: $GITLAB_TOKEN"
```

## URL-Encoding Project IDs

GitLab API requires URL-encoded project paths. Encode `/` as `%2F`:

- `chatmeter/dashboard` → `chatmeter%2Fdashboard`
- `chatmeter/api-server` → `chatmeter%2Fapi-server`

When you know the numeric project ID, use that instead — no encoding needed.

## Project IDs

All projects live under the `chatmeter` namespace on GitLab. Use numeric IDs in API calls.

| Project                  | ID       |
|--------------------------|----------|
| monorepo (aka chatmeter) | 39261945 |
| prompty                  | 47185722 |
| jukebox                  | 38790169 |
| etl                      | 38609162 |
| astronaut                | 46336910 |
| chatmeter-skills         | 77300207 |
| deploy-utility           | 38969702 |
| pw-integration-tests     | 59833987 |
| data-science2            | 38609878 |
| survey-renderer          | 43828360 |
| nightcrawler             | 38895345 |
| heisenberg               | 72549558 |
| mongo-administration     | 38787444 |
| engineering              | 38609000 |
| custom-reports           | 68790918 |
| lurch                    | 38609149 |
| argonaut                 | 38917455 |
| api-docs                 | 38609519 |
| css-inliner              | 38609475 |
| instant-audit-client     | 38609441 |
| webhookup                | 38709539 |
| integration-tests        | 38969349 |

## Team Members

Rommel's direct reports. Prioritize these when listing MRs, but do not filter out other authors.

| Name     | GitLab Username |
|----------|-----------------|
| Adam     | agallagher1     |
| Fele     | fcrear          |
| Mitchell | mszeto          |
| Rommel   | rommel-rico     |

## Fetch Open MRs

List all open merge requests visible to the token:

```bash
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$GITLAB_URL/api/v4/merge_requests?state=opened&scope=all&per_page=20"
```

Useful query parameters:

| Parameter          | Example                        | Purpose                        |
|--------------------|--------------------------------|--------------------------------|
| `author_username`  | `mitchell`                     | Filter by author               |
| `reviewer_username`| `rommel`                       | MRs where you are reviewer     |
| `project_id`       | `42`                           | Limit to one project           |
| `labels`           | `needs-review`                 | Filter by label                |
| `scope`            | `assigned_to_me`               | MRs assigned to you            |
| `order_by`         | `updated_at`                   | Sort field                     |
| `sort`             | `desc`                         | Sort direction                 |

When summarizing for voice, group by author and lead with what needs attention (blocked, failing pipeline, waiting on review).

## Fetch MR Details and Diff

Get MR metadata:

```bash
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$GITLAB_URL/api/v4/projects/:id/merge_requests/:iid"
```

Get the diff (for code review):

```bash
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$GITLAB_URL/api/v4/projects/:id/merge_requests/:iid/changes"
```

The `changes` response includes a `changes` array. Each entry has `old_path`, `new_path`, and `diff` fields.

When reviewing:
- Focus on architectural concerns, code smells, structural flaws, missing abstractions
- Check test coverage: happy path, sad path, bad path — note gaps
- Surface what is done well, be specific
- Pose feedback as questions or suggestions unless something is a must-fix
- Do not narrate the diff — summarize what matters

## Post a Comment

Post a general note on an MR:

```bash
curl -s -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"body": "Your comment here"}' \
  "$GITLAB_URL/api/v4/projects/:id/merge_requests/:iid/notes"
```

Before posting, confirm with the user what the comment should say. Read it back for approval if the wording matters.

## Check Pipeline Status

Get pipelines for a branch or MR:

```bash
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$GITLAB_URL/api/v4/projects/:id/pipelines?ref=:branch&per_page=5"
```

Get jobs for a specific pipeline:

```bash
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "$GITLAB_URL/api/v4/projects/:id/pipelines/:pipeline_id/jobs"
```

When reporting pipeline status:
- Lead with pass/fail
- If failed, name the failing job(s) and stage
- Skip successful jobs unless asked for detail

## Common Workflows

### "What MRs are open?" / "What needs my review?"

1. Fetch open MRs (use `reviewer_username` or `scope=assigned_to_me` as appropriate)
2. Summarize: count, grouped by author, flag any with failing pipelines or stale activity

### "Review [author]'s latest MR"

1. Fetch open MRs filtered by `author_username`
2. Pick the most recently updated one
3. Fetch the diff via `/changes`
4. Review using the code review approach above
5. Summarize findings for voice — short sentences, what matters, skip nits

### "Leave a comment that..."

1. Identify the target MR (ask if ambiguous)
2. Compose the comment from the user's intent
3. Read it back for confirmation
4. Post via the notes endpoint
5. Confirm it was posted

## Voice Formatting

- Short sentences. Active voice. No filler.
- Lead with what needs attention.
- Do not read JSON or data verbatim — interpret it first.
- Keep total spoken output under 30 seconds unless the user asks for detail.
