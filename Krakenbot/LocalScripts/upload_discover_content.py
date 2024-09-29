import glob
import sys
import mammoth
from markdownify import markdownify
from pathlib import Path

# If run directly, other folders' package can't be imported due to path issue
# Set the path to parent path ('./MachD/Krakenbot) instead of current path
if __name__ == '__main__':
	file = Path(__file__).resolve()
	sys.path.append(str(file.parents[1]))

from models.firebase_discover import FirebaseDiscover

def main():
    input_dir = '.\\Krakenbot\\LocalScripts\\discover\\'
    firebase = FirebaseDiscover()

    for file in glob.glob(input_dir + '*.docx'):
        print(f'Processing {file}')
        token_id = file.split('\\')[-1].removesuffix('.docx').upper()
        with open(file, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file)
            html = result.value
            md = markdownify(html)
            firebase.save(token_id, md)

    for file in glob.glob(input_dir + '*.md'):
        print(f'Processing {file}')
        token_id = file.split('\\')[-1].removesuffix('.md').upper()
        with open(file, "r", encoding='utf-8') as md_file:
            markdown = md_file.read().replace('\n', '<br/>')
            firebase.save(token_id, markdown)

if __name__ == '__main__':
    main()
    print('Done')
