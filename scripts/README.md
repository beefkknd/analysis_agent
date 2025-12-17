# Scripts

Utility scripts for the BI Agent project.

## Archive Scripts (Email-Friendly Packaging)

These scripts package and unpackage the entire project as plain text files that can be safely sent via email (bypassing zip file restrictions).

### `zip_file.sh` - Create Plain Text Archive

Packages all project files into a single plain text file.

**Usage:**
```bash
# Default: creates output/project_archive.txt with unlimited lines per file
./scripts/zip_file.sh

# Custom output file
./scripts/zip_file.sh my_backup.txt

# Limit to 500 lines per file (for very large files)
./scripts/zip_file.sh output/project_archive.txt 500
```

**What it includes:**
- All `.py`, `.sh`, `.yaml`, `.yml`, `.json`, `.md` files
- Core directories: config, domain, services, tools, nodes, routing, memory, mcp_server, scripts
- Root files: graph.py, agent.py, README.md, ARCHITECTURE.md, .env.example, requirements.txt

**What it excludes:**
- Hidden files (`.git`, `.env`, etc.)
- `__pycache__`, `*.pyc`
- `__init__.py` files
- Test files and directories
- Virtual environments
- Build/dist directories
- Output directory (doesn't archive itself)

**Output format:**
```
===== FILE: path/to/file.py =====
[file contents]
===== END FILE =====
```

### `unzip_file.sh` - Restore from Archive

Extracts files from the plain text archive and recreates the project structure.

**Usage:**
```bash
# Default: extracts output/project_archive.txt to output/restored_project/
./scripts/unzip_file.sh

# Custom input file
./scripts/unzip_file.sh my_backup.txt

# Custom target directory
./scripts/unzip_file.sh output/project_archive.txt ./my_restored_project
```

**Features:**
- Automatically creates directory structure
- Sets proper permissions (makes `.py` and `.sh` files executable)
- Preserves file content exactly

### Email Workflow

1. **Package project:**
   ```bash
   cd /path/to/my_cbp_agent
   ./scripts/zip_file.sh
   ```

2. **Send via email:**
   - Attach `output/project_archive.txt` to your email
   - Text files are rarely blocked by email servers

3. **Restore on another machine:**
   ```bash
   # Save the received project_archive.txt file
   mkdir -p my_cbp_agent/scripts
   cd my_cbp_agent

   # Copy the unzip script (or download it first)
   ./scripts/unzip_file.sh /path/to/received/project_archive.txt

   # Project restored to output/restored_project/
   cd output/restored_project
   cp .env.example .env
   # Edit .env with your API keys
   pip install -r requirements.txt
   python agent.py
   ```

### Tips

- **File size:** The plain text archive will be larger than a zip file (no compression), but typically still email-friendly (< 10MB for most projects)
- **Line limit:** Use the 500-line limit if you have very large files and want to reduce email size
- **Verification:** After extraction, verify file counts match the metadata at the end of the archive
- **Version control:** The archive includes a timestamp, making it easy to track when it was created

### Troubleshooting

**"Permission denied" when running scripts:**
```bash
chmod +x scripts/*.sh
```

**Archive file not found during extraction:**
```bash
# Make sure you're in the project root
./scripts/unzip_file.sh output/project_archive.txt
```

**Missing files after extraction:**
- Check the archive metadata at the end of the file for file count
- Verify the original archive completed successfully (check the footer)
