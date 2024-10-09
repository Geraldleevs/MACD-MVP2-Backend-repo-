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

style_map = """
p[style-name='Heading 1'] => h1:fresh
p[style-name='Heading 2'] => h2:fresh
"""

def main():
    input_dir = '.\\Krakenbot\\LocalScripts\\discover\\'
    firebase = FirebaseDiscover()

    for file in glob.glob(input_dir + '[a-zA-Z0-9]*.docx'):
        print(f'Processing {file}')

        print('======== Content Starts Here ========')
        token_id = file.split('\\')[-1].removesuffix('.docx').upper()
        with open(file, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file, style_map=style_map, ignore_empty_paragraphs=False)
            html = result.value.replace('<p></p>', '<hr/>') # Empty lines as separator line (Because empty lines do not show on FlutterFlow)
            md = markdownify(html, heading_style='ATX')
            print(md)
        print('========= Content Ends Here =========')

        decision = input(f'Confirm Save {token_id}? (Enter "Y" to save):')
        if decision.lower() == 'y':
            firebase.save(token_id, md)
            print(f'{token_id} is saved!')
        else:
            print(f'{token_id} is not saved!')

if __name__ == '__main__':
    main()
    print('Done')
