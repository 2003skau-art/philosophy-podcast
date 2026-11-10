import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from llm import candidates

print("Models the pipeline will try, in order:")
for p, m in candidates():
    print(f"  {p}: {m}")