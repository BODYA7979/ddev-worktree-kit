<!-- #ddev-generated -->
<!-- worktree-kit:start -->
## DDEV Worktree Kit

- Use the agent client's worktree mode. Native hooks prepare the assigned checkout and DDEV; reuse that checkout.
- Run DDEV commands from the current worktree. Inspect its URL/state with `ddev wtk status`.
- Resolve setup errors before application work. Never edit ownership/seed receipts to bypass checks.
- Preserve the worktree database; reset, reseed and deployment commands require the task's explicit intent.
- Check file strategy before changing uploads: `shared` writes affect the source directory.
- Let native cleanup manage its owned worktree. Manual GC starts with `ddev wtk gc` preview.
<!-- worktree-kit:end -->
