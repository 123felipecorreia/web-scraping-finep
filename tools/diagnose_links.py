from pathlib import Path
import Main

p_root = Path(Main.__file__).resolve().parent
print('PROJECT_ROOT:', p_root)
links_folder = Path(Main.LINKS_FOLDER).resolve()
print('LINKS_FOLDER:', links_folder, 'exists=', links_folder.exists())

print('\nContents of project root:')
for e in sorted(p_root.iterdir()):
    print(' -', e.name, 'DIR' if e.is_dir() else 'FILE')

print('\nContents of LINKS_FOLDER:')
if links_folder.exists():
    for e in sorted(links_folder.iterdir()):
        try:
            st = e.stat()
            print(' -', e.name, 'is_file=', e.is_file(), 'is_dir=', e.is_dir(), 'size=', st.st_size)
        except Exception as ex:
            print(' -', e.name, 'stat-error:', ex)
else:
    print(' LINKS_FOLDER does not exist')

# Check for suspicious "LLinks" path
susp = p_root / 'LLinks' / 'meu_arquivo.xlsx'
print('\nSuspicious path to check:', susp)
print(' Exists:', susp.exists())
print(' Is file:', susp.is_file())
print(' Is dir:', susp.is_dir())

# Also check the actual path from earlier error: Links\meu_arquivo.xlsx
errp = p_root / 'Links' / 'meu_arquivo.xlsx'
print('\nExpected path:', errp)
print(' Exists:', errp.exists())
print(' Is file:', errp.is_file())
print(' Is dir:', errp.is_dir())

# Check data folder
data_dir = p_root / 'data'
print('\nData folder:', data_dir, 'exists=', data_dir.exists())
if data_dir.exists():
    for e in sorted(data_dir.iterdir()):
        print(' -', e.name, 'is_file=', e.is_file(), 'is_dir=', e.is_dir())
