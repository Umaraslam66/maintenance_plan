Test the tool using following commands:

# Check that all necessary directories exist
ls -la data/input data/processed data/output src/*/

# Activate virtual environment (if using one)
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Verify Python dependencies
pip list | grep -E 'pandas|numpy|pyscipopt|matplotlib|networkx|streamlit|plotly'

# Test module imports
python -c "from src.optimization_models.plan_data import Network, Plan; print('Network module OK')"
python -c "from src.optimization_models.proj_sched import ProjectSchedulingModel; print('Scheduling module OK')"
python -c "from src.optimization_models.traffic_flow import TrafficFlowModel; print('Traffic module OK')"
python -c "from src.execution.tcr_opt import TCROptimizer; print('Optimizer module OK')"

# Check network data
python -c "import xml.etree.ElementTree as ET; tree = ET.parse('data/processed/network.xml'); print(f'Network has {len(tree.findall(\".//node\"))} nodes and {len(tree.findall(\".//link\"))} links')"

# Check traffic data
python -c "import xml.etree.ElementTree as ET; tree = ET.parse('data/processed/traffic.xml'); print(f'Traffic data has {len(tree.findall(\".//line\"))} lines and {len(tree.findall(\".//demand\"))} demand entries')"

# Check project data
python -c "import xml.etree.ElementTree as ET; tree = ET.parse('data/processed/projects.xml'); print(f'Project data has {len(tree.findall(\".//project\"))} projects and {len(tree.findall(\".//task\"))} tasks')"

# Run traffic-only optimization
python src/execution/run.py --file data/processed/problem.xml --opt traf --prt_vlvl 2 --out_dir results/test_traffic

# Schedule projects only
python src/execution/run.py --file problem.xml --dir data/processed --opt proj --out_dir results/test_sched --time_filter v2410,v2426
# Traffic updated command 
python src/execution/run.py --file problem.xml --dir data/processed --opt traf --out_dir results/test_traffic

# Analyze traffic impacts
python src/execution/run.py --file problem.xml --opt traf --inp_capuse ./results/capacity_blocks.xml

# Main Execution 
python src/execution/run.py --file problem.xml --dir ./data --opt both --out_dir ./results

# Test with time filter for weeks 10-26 (as in the case study)
python src/execution/run.py --file data/processed/problem.xml --opt both --time_filter v2410,v2426 --prt_vlvl 2 --out_dir results/test_case_study

# Extract key statistics from results
python -c "
import xml.etree.ElementTree as ET
import os

# Check schedule
sched_file = 'results/test_integrated/schedule_results.xml'
if os.path.exists(sched_file):
    tree = ET.parse(sched_file)
    print(f'Schedule has {len(tree.findall(\".//project\"))} scheduled projects')
    print(f'With {len(tree.findall(\".//instance\"))} task instances')
    print(f'Affecting {len(tree.findall(\".//day\"))} traffic days')

# Check traffic impact
traffic_file = 'results/test_integrated/traffic_results.xml'
if os.path.exists(traffic_file):
    tree = ET.parse(traffic_file)
    summary = tree.find('.//summary')
    if summary is not None:
        print(f'Cancelled trains: {summary.findtext(\"cancelled\")}')
        print(f'Delayed trains: {summary.findtext(\"delayed\")}')
        print(f'Diverted trains: {summary.findtext(\"diverted\")}')
"