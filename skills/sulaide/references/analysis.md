# Review each page's content and visual goal

Read `interaction.md`. Start analysis after the settings checkpoint is answered, or for an explicit reanalysis request with a resolved target. Analysis completion opens page review; it does not start images.

Sulaide performs analysis and style recommendation through the CLI. The host explains returned content, collects the user's visual goals and presents public style descriptions. Do not fetch private prompts, implement a substitute style selector or present a locally drafted analysis as a service result.

## Analyse and establish the review

1. Read `sulaide projects show PROJECT_ID`; retain source revision, active presentation ID and confirmed settings.
2. Run `sulaide analysis start PROJECT_ID --expected-revision REVISION [--page-count N] [--structure-requirements "..."]`.
3. Keep operation/run IDs. Use `sulaide wait OPERATION_ID --timeout 180`; after interruption inspect the original operation. A timeout never authorizes another analysis request.
4. On completion, read the project, `sulaide layout show PROJECT_ID`, `sulaide visual-styles list` and capabilities from `sulaide auth status`. Analysis can promote a new active version: refresh source, active, editing version and manifest revision together.
5. Give a short section/page overview, then start with the first unreviewed page. The overview is navigation, not approval of all page content.

The website's reanalysis count is **1–50**, starting from current pages; changing it replaces the outline, so explain the impact first. Its “结构要求” input allows 2000 characters; the CLI/API's existing 4000-character compatibility limit is not an extra website option. Collect it only when the user needs structural guidance.

## A page the user can understand

Show four things together:

- **What this page should communicate:** the intended takeaway, grounded in its returned content. Label a host interpretation as a suggested takeaway if the service does not state one.
- **What will actually appear:** its main points, important numbers, conditions and relationships. A title alone is insufficient; do not invent facts to fill the page or silently remove necessary qualifiers to make it shorter.
- **Proposed visual goal:** how to express it: for example restrained density, fewer words, more photographs, a diagram, or visible connections. These descriptions can combine. They do not require the user to learn style names, and are not a new fixed enum.
- **Current/recommended style and expected effect:** use the service's returned style ID with the live public catalog description. Distinguish a user override from a recommendation. Explain the visible result, without inventing internal scores or reasons.

For example, a page about three systems might aim for “极简、少量文字，用三个模块和连接线突出数据流向”. Present that as a proposal, not a rendered preview or a hard-coded mapping to a particular style. The service chooses the matching style.

Offer “确认本页并继续／修改内容／调整呈现目标”, with free-text replies accepted. Retain prior explicit choices. A one-page reply does not approve remaining pages, generation or export.

## Save the goal and read the service's choice

`visual_presentation_goals: true` in capabilities is required before sending a goal. If absent, explain that this server cannot save and apply page goals; offer updating the service. A website handoff may use its existing content/style controls only: do not claim it can save or apply this new goal field unless that website capability has been verified. Do not submit an unknown field, pretend that conversation text was saved, or replace server matching with host matching.

When the user confirms or supplies a goal:

1. Read the current layout and match the page's stable `slide_id` to the content they reviewed. A changed identity or content needs affected-page review; do not silently renew an old approval.
2. Save only the requested fields with `sulaide pages edit P N --visual-goal "USER_GOAL" --expected-version V --expected-revision R`. Goals allow up to 2000 characters; preserve their meaning. An empty string clears a goal; omitting the flag preserves it. Do not put the goal into `--narrative`, `--content` or a private prompt field.
3. Read the project/layout again. Show the saved `visual_goal`, current style and `visual_style_recommendation.style_id` using public catalog descriptions. The service owns matching. Goal changes can invalidate old images/preparation, even when the style ID stays the same.
4. Preserve an explicit user style. If the returned recommendation differs from that override, show both and ask whether to keep the override or apply the returned recommendation through the existing guarded `--visual-style` edit. Do not silently replace the user's style.
5. If the saved outcome matches what the user accepted, acknowledge it and proceed to the next page. If it changes the reviewed effect materially, keep this page pending for confirmation. Once every applicable page is reviewed, show a compact final content/goal/style summary and ask to generate. An explicit last-page-and-generate reply may authorize both.

Batch only when the user expressly asks, such as “后面沿用这个方向”. State the covered pages, preserve earlier page-specific choices and record each write/new identity. On a partial batch failure, report completed and remaining pages; recover an uncertain operation before continuing. Do not broaden one-page changes into whole-deck edits.

Frozen-template section/end pages still participate in content review, but keep their fixed template. Explain that appearance and available theme/template controls; do not save an unsupported AI goal or style. Use returned render/template metadata, never page position, to identify them.

## Editing the outline

Before each write, read the editing identity and confirm the affected content. Pass `--expected-version V --expected-revision R`, including reanalysis. Send only changed fields; an edit is not permission to generate.

| Requested action | Command | Relevant limit |
|---|---|---|
| Change title/subtitle/body/core narrative | `pages edit P N --title ... --subtitle ... --content ... --narrative ...` | `--content-file F` is available for longer text. |
| Save/clear visual goal | `pages edit P N --visual-goal "..."` | Up to 2000 characters; empty clears, omitted preserves. Requires goal capability. |
| Apply an explicitly chosen style | `pages edit P N --visual-style ID` | Live catalog ID, applicable AI page. |
| Adjust title/subtitle width | `pages edit P N --title-width 800 --subtitle-width 700` | Advanced only; website canvas constraints apply. |
| Add/delete/duplicate/move | `pages add P --after N`, `pages delete P N`, `pages duplicate P N`, `pages move P N up or down` | Preserve structure rules and stable page identity. |
| Split | `pages split P N --at OFFSET` | Resolve the split with the user; derive the character offset internally. |
| Merge into previous | `pages merge P N` | Same section; page N merges into N−1. |
| Reanalyse one page | `pages reanalyze P N --instruction "..."` | Only that page; include version guards. |

Chapter movement and undo of split/merge remain website-only. Split/merge generate titles in a billed background run; retain its request/run IDs and recover the original operation on timeout. Use distinct request IDs for distinct edits.

After content changes, show affected pages and revisit their goals/styles where needed; preserve unrelated confirmations. HTTP 409 requires a reread and renewed affected-page review, not automatic retry with new guards. When generation is authorized, hand the exact source, active, editing and manifest identities plus saved goals and operation references to `preview.md`.
