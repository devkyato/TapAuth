# Contributing to TapAuth

TapAuth is a personal project, but I am happy to review focused improvements that keep the kiosk dependable and understandable.

1. Fork the repository and create one branch for one clear change.
2. Keep the interface lightweight and usable at 1366 × 700.
3. Never commit `.env`, student records, database exports, NFC UIDs, or server credentials.
4. Run the checks listed in the README.
5. Explain what changed, why it matters at the kiosk, and how you verified it.

For NFC changes, mention the reader model and Raspberry Pi OS version you tested. For database changes, keep `schema.sql` safe to run on an existing installation.

Oh! If a change adds a dependency, please explain why the Pi needs it. Keeping the runtime small is part of the project.

## Release checklist

Before I call a TapAuth release ready, I check:

- `APP_CONFIG["version"]`, `.zenodo.json`, `CITATION.cff`, README installation
  and citation text, changelog, and release notes all use the same version and
  release date;
- `.zenodo.json` parses and its description uses only the supported HTML
  elements;
- `CITATION.cff` validates and contains no unassigned DOI or ORCID;
- Python compilation, JavaScript syntax checks, JSON checks, and the complete
  unit-test suite from the README pass;
- setup and update shell scripts pass `bash -n`;
- a target Pi backup exists and setup/update, service status, ACR122U recovery,
  registration, repeat recognition, and enabled reconciliation paths have
  been checked;
- the archive contains no `.env`, credentials, records, database exports,
  service-account files, NFC UIDs, or local registry data.
