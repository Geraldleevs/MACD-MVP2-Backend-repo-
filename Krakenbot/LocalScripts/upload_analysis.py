import sys
import pandas as pd
from pathlib import Path

# If run directly, other folders' package can't be imported due to path issue
# Set the path to parent path ('./MachD/Krakenbot) instead of current path
if __name__ == '__main__':
	file = Path(__file__).resolve()
	sys.path.append(str(file.parents[1]))

from models.firebase_analysis import FirebaseAnalysis

def __main():
	# Change The file if needed
	input_file = '.\\Krakenbot\\LocalScripts\\analysis.csv'
	# The columns should be
	# tokens, risk, goal_length, summary, analysis, technical_analysis
	# tokens is just token id, e.g. BTC

	# =================================================
	#   Do not need to change from this line onwards
	# =================================================
	firebase = FirebaseAnalysis()
	cols = ['tokens', 'risk', 'goal_length', 'summary', 'analysis', 'technical_analysis']
	df = pd.read_csv(input_file)
	df = df.fillna('')
	df.columns = cols

	for token in df['tokens'].unique():
		analysis = []
		for _, token_df in df[df['tokens'] == token].iterrows():
			analysis.append({
				'goal_length': token_df['goal_length'],
				'risk': token_df['risk'],
				'summary': token_df['summary'],
				'analysis': token_df['analysis'],
				'technical_analysis': token_df['technical_analysis'],
			})
		firebase.save(token, analysis)

if __name__ == '__main__':
	__main()
	print('Done')
