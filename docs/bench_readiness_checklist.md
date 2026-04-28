# Bench Readiness Checklist

This checklist tracks the transformation of `company_creation` into a bench-ready Frappe app.

## 1) Baseline status

- [x] App package exists: `company_creation/`
- [x] Core app files exist: `hooks.py`, `modules.txt`, `patches.txt`
- [x] Build metadata exists: `pyproject.toml`
- [ ] Legacy-compatible packaging file exists: `setup.py`
- [ ] Package data manifest exists: `MANIFEST.in`
- [ ] Standard desk config entry exists: `company_creation/config/desktop.py`
- [ ] `__init__.py` present in all DocType package directories
- [ ] DocType controller naming conventions fully aligned
- [ ] Naming normalization migration patches added
- [ ] README includes production-grade bench install/migrate/operate guide

## 2) Validation commands (to run in bench context)

```bash
bench get-app <repo-url>
bench --site <site-name> install-app company_creation
bench --site <site-name> migrate
bench --site <site-name> run-tests --app company_creation
```

## 3) Notes

- Do not delete existing files/folders without explicit approval.
- Prefer additive and migration-safe changes.
