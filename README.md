# RippleWin (Offline WinForms + SQLite JSON1)

- Paste text on the left → **Ingest**
- See derived fields on the right (Keywords, Metaphors, Structure, Strategy, Summary, Humanized)
- Search box supports:
  - free text (e.g., `dirty`)
  - `topic:Buffers`
  - `metaphor:solvent`
  - `hasStrategy:true`

## Build
- Visual Studio 2022+
- .NET 8 SDK
- NuGet: Microsoft.Data.Sqlite

## Storage
- `%LocalAppData%/RippleWin/ripple.db` (WAL mode)
