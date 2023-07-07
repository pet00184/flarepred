import post_analysis as pa
import importlib
importlib.reload(pa)

pra = pa.PostRunAnalysis('HISTORICAL_TEST_1')

print(pra.summary_times['Realtime Trigger'])