# src/visualization/dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import networkx as nx
import xml.etree.ElementTree as ET
import os
import sys
from datetime import datetime
import plotly.express as px
import plotly.figure_factory as ff
import numpy as np

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from execution.tcr_opt import TCROptimizer
from optimization_models.plan_data import Network

# Page configuration
st.set_page_config(
    page_title="Dashboard",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar for navigation
st.sidebar.title("Railway Maintenance Planning Tool") 
page = st.sidebar.radio("Go to", ["Home", "Project Setup", "Optimization", "Schedule Viewer", "Network Visualization", "Traffic Impact"])

# Header
st.title("Railway Planning Dashboard")
st.markdown("---")

def load_network_data(file_path):
    """Load network data from XML file"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Create network
        network = Network()
        
        # Parse nodes
        nodes_elem = root.find('nodes')
        if nodes_elem is not None:
            for node_elem in nodes_elem.findall('node'):
                node_id = node_elem.get('id')
                name = node_elem.get('name')
                lat = float(node_elem.get('lat')) if node_elem.get('lat') is not None else None
                lon = float(node_elem.get('lon')) if node_elem.get('lon') is not None else None
                merge_group = node_elem.get('merge_group')
                
                network.add_node(node_id, name, lat, lon, merge_group)
        
        # Parse links
        links_elem = root.find('links')
        if links_elem is not None:
            for link_elem in links_elem.findall('link'):
                link_id = link_elem.get('id')
                from_node = link_elem.get('from')
                to_node = link_elem.get('to')
                length = float(link_elem.get('length')) if link_elem.get('length') is not None else None
                tracks = int(link_elem.get('tracks')) if link_elem.get('tracks') is not None else None
                capacity = int(link_elem.get('capacity')) if link_elem.get('capacity') is not None else 10
                
                network.add_link(link_id, from_node, to_node, length, tracks, capacity)
        
        return network
    except Exception as e:
        st.error(f"Error loading network data: {e}")
        return None

def load_schedule_data(file_path):
    """Load schedule data from XML file"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Extract project schedule data
        projects = []
        for proj_elem in root.findall('.//project'):
            proj_id = proj_elem.get('id')
            proj_desc = proj_elem.get('desc', '')
            
            for task_elem in proj_elem.findall('.//task'):
                task_id = task_elem.get('id')
                task_desc = task_elem.get('desc', '')
                duration = float(task_elem.get('duration', 0))
                
                for inst_elem in task_elem.findall('.//instance'):
                    index = int(inst_elem.get('index', 0))
                    start = datetime.strptime(inst_elem.get('start'), "%Y-%m-%d %H:%M:%S")
                    end = datetime.strptime(inst_elem.get('end'), "%Y-%m-%d %H:%M:%S")
                    
                    projects.append({
                        'Project': proj_id,
                        'Project Description': proj_desc,
                        'Task': task_id,
                        'Task Description': task_desc,
                        'Instance': index,
                        'Start': start,
                        'End': end,
                        'Duration (hours)': duration
                    })
        
        return pd.DataFrame(projects)
    except Exception as e:
        st.error(f"Error loading schedule data: {e}")
        return None

def load_capacity_data(file_path):
    """Load capacity utilization data from XML file"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Extract capacity utilization data
        utilization = []
        for util_elem in root.findall('.//util'):
            link_id = util_elem.get('link')
            period = int(util_elem.get('period'))
            start = datetime.strptime(util_elem.get('start'), "%Y-%m-%d %H:%M:%S")
            value = float(util_elem.get('value'))
            
            utilization.append({
                'Link': link_id,
                'Period': period,
                'Start': start,
                'Utilization': value
            })
        
        return pd.DataFrame(utilization)
    except Exception as e:
        st.error(f"Error loading capacity data: {e}")
        return None

def load_traffic_impact(file_path):
    """Load traffic impact data from XML file"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Extract summary data
        summary = {}
        summary_elem = root.find('.//summary')
        if summary_elem is not None:
            summary['cancelled'] = float(summary_elem.findtext('cancelled', '0'))
            summary['delayed'] = float(summary_elem.findtext('delayed', '0'))
            summary['diverted'] = float(summary_elem.findtext('diverted', '0'))
        
        # Extract flow data
        flows = []
        for flow_elem in root.findall('.//flow'):
            line = flow_elem.get('line')
            route = flow_elem.get('route')
            period = int(flow_elem.get('period'))
            value = float(flow_elem.get('value'))
            
            flows.append({
                'Line': line,
                'Route': route,
                'Period': period,
                'Value': value
            })
        
        return summary, pd.DataFrame(flows)
    except Exception as e:
        st.error(f"Error loading traffic impact data: {e}")
        return None, None

def create_gantt_chart(df):
    """Create a Gantt chart for project schedule using Plotly"""
    if df is None or len(df) == 0:
        return None
    
    # Format data for gantt chart
    gantt_data = []
    
    for _, row in df.iterrows():
        gantt_data.append(dict(
            Task=f"{row['Project']}-{row['Task']}",
            Description=row['Task Description'],
            Start=row['Start'],
            Finish=row['End'],
            Resource=row['Project Description']
        ))
    
    fig = ff.create_gantt(
        gantt_data,
        colors={res: f'rgb({50+i*30}, {100+i*20}, {150+i*10})' 
                for i, res in enumerate(df['Project Description'].unique())},
        index_col='Resource',
        show_colorbar=True,
        group_tasks=True,
        showgrid_x=True,
        showgrid_y=True,
        title='Project Schedule'
    )
    
    fig.update_layout(
        autosize=True,
        height=600,
        margin=dict(l=50, r=50, b=100, t=80, pad=4)
    )
    
    return fig

def create_network_visualization(network, capacity_df=None):
    """Create network visualization with capacity utilization"""
    if network is None:
        return None
    
    # Create graph
    G = nx.Graph()
    
    # Add nodes
    node_pos = {}
    for node_id, node in network.nodes.items():
        G.add_node(node_id, name=node.get('name', node_id))
        if 'lon' in node and 'lat' in node:
            node_pos[node_id] = (node['lon'], node['lat'])
    
    # If no position info, use spring layout
    if not node_pos:
        node_pos = nx.spring_layout(G)
    
    # Add links
    for link_id, link in network.links.items():
        from_node = link['from_node']
        to_node = link['to_node']
        G.add_edge(from_node, to_node, id=link_id)
    
    # Load capacity utilization if available
    if capacity_df is not None:
        # Get maximum capacity utilization for each link
        link_utilization = {}
        for _, row in capacity_df.iterrows():
            link_id = row['Link']
            value = row['Utilization']
            
            if link_id not in link_utilization or value > link_utilization[link_id]:
                link_utilization[link_id] = value
        
        # Create edge color mapping
        edge_colors = {}
        max_util = max(link_utilization.values()) if link_utilization else 1.0
        
        for link_id, util in link_utilization.items():
            # Normalize utilization (0-1)
            norm_util = util / max_util
            # Color gradient: green (0) to red (1)
            edge_colors[link_id] = f'rgb({int(255*norm_util)}, {int(255*(1-norm_util))}, 0)'
    
    # Create node trace
    node_trace = {
        'x': [pos[0] for pos in node_pos.values()],
        'y': [pos[1] for pos in node_pos.values()],
        'text': list(node_pos.keys()),
        'mode': 'markers+text',
        'hoverinfo': 'text',
        'marker': {
            'size': 10,
            'color': 'lightblue'
        },
        'textposition': 'top center'
    }
    
    # Create edge traces
    edge_traces = []
    for u, v, data in G.edges(data=True):
        link_id = data.get('id', f"{u}-{v}")
        x0, y0 = node_pos[u]
        x1, y1 = node_pos[v]
        
        color = edge_colors.get(link_id, 'gray') if capacity_df is not None else 'gray'
        
        edge_trace = {
            'x': [x0, x1],
            'y': [y0, y1],
            'mode': 'lines',
            'line': {
                'width': 2,
                'color': color
            },
            'hoverinfo': 'text',
            'text': link_id
        }
        edge_traces.append(edge_trace)
    
    # Create figure
    layout = {
        'title': 'Railway Network with Capacity Utilization',
        'showlegend': False,
        'hovermode': 'closest',
        'margin': {'b': 20, 'l': 20, 'r': 20, 't': 40},
        'xaxis': {'showgrid': False, 'zeroline': False, 'showticklabels': False},
        'yaxis': {'showgrid': False, 'zeroline': False, 'showticklabels': False},
        'height': 600
    }
    
    fig = {
        'data': edge_traces + [node_trace],
        'layout': layout
    }
    
    return fig

def create_traffic_impact_chart(summary, flows_df=None):
    """Create charts for traffic impact"""
    if summary is None:
        return None, None
    
    # Create summary pie chart
    impact_data = pd.DataFrame([
        {'Category': 'Cancelled', 'Count': summary['cancelled']},
        {'Category': 'Delayed', 'Count': summary['delayed']},
        {'Category': 'Diverted', 'Count': summary['diverted']}
    ])
    
    fig1 = px.pie(
        impact_data, 
        values='Count', 
        names='Category', 
        title='Traffic Impact Summary',
        color='Category',
        color_discrete_map={
            'Cancelled': 'red',
            'Delayed': 'orange',
            'Diverted': 'yellow'
        }
    )
    
    # Create flows bar chart if data available
    fig2 = None
    if flows_df is not None and len(flows_df) > 0:
        # Group by line and route
        flow_summary = flows_df.groupby(['Line', 'Route'])['Value'].sum().reset_index()
        flow_summary = flow_summary.sort_values('Value', ascending=False).head(20)  # Top 20
        
        fig2 = px.bar(
            flow_summary,
            x='Line',
            y='Value',
            color='Route',
            title='Top 20 Traffic Flows',
            labels={'Line': 'Traffic Line', 'Value': 'Flow Volume', 'Route': 'Route Type'}
        )
    
    return fig1, fig2

# Home page
if page == "Home":
    st.header("Welcome to Railway Maintenance Planning Dashboard")
    
    st.markdown("""
    This dashboard provides an interface to the railway planning tool, which optimizes track work scheduling 
    and traffic flows. Use the sidebar to navigate between different sections:
    
    - **Project Setup**: Load project data and configure parameters
    - **Optimization**: Run optimization models and view progress
    - **Schedule Viewer**: View the optimized project schedule as a Gantt chart
    - **Network Visualization**: View the railway network with capacity utilization
    - **Traffic Impact**: Analyze the impact of scheduled works on train traffic
    
    ### Getting Started
    
    1. Navigate to **Project Setup** to load your project data
    2. Configure optimization parameters
    3. Run the optimization in the **Optimization** page
    4. View results in the visualization pages
    """)
    
    # Dashboard statistics
    st.subheader("Dashboard Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Projects", value="0", delta=None)
    
    with col2:
        st.metric(label="Scheduled Tasks", value="0", delta=None)
    
    with col3:
        st.metric(label="Affected Traffic Days", value="0", delta=None)

# Project Setup page
elif page == "Project Setup":
    st.header("Project Setup")
    
    # File upload section
    st.subheader("Data Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        network_file = st.file_uploader("Upload Network XML", type=["xml"])
        projects_file = st.file_uploader("Upload Projects XML", type=["xml"])
    
    with col2:
        traffic_file = st.file_uploader("Upload Traffic XML", type=["xml"])
        params_file = st.file_uploader("Upload Parameters XML", type=["xml"])
    
    # Or use example data
    st.markdown("---")
    st.subheader("Or use example data")
    
    if st.button("Load Example Data"):
        st.success("Example data loaded successfully!")
    
    # Parameter configuration
    st.markdown("---")
    st.subheader("Optimization Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.number_input("Time Period Length (hours)", min_value=1, max_value=24, value=8, step=1)
        st.selectbox("Optimization Type", ["Scheduling Only", "Traffic Only", "Integrated"])
    
    with col2:
        st.number_input("Time Limit (seconds)", min_value=10, max_value=7200, value=3600, step=10)
        st.number_input("Optimality Gap", min_value=0.001, max_value=0.1, value=0.01, step=0.001, format="%.3f")
    
    st.text_area("Additional Arguments", height=100, placeholder="--proj_filter=214,180,526 --time_filter=v2410,v2426")
    
    if st.button("Save Configuration"):
        st.success("Configuration saved successfully!")

# Optimization page
elif page == "Optimization":
    st.header("Optimization")
    
    # Run optimization section
    st.subheader("Run Optimization")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.selectbox("Optimization Mode", ["Scheduling", "Traffic Flow", "Integrated"], key="opt_mode")
    
    with col2:
        st.checkbox("Use Fixed Track Closures", value=False)
    
    with col3:
        st.checkbox("Save Intermediate Results", value=True)
    
    if st.button("Start Optimization"):
        # Show progress bar
        progress = st.progress(0)
        status = st.empty()
        
        # Simulate optimization progress
        for i in range(101):
            progress.progress(i)
            if i < 10:
                status.info("Initializing optimization...")
            elif i < 30:
                status.info("Building models...")
            elif i < 60:
                status.info("Solving scheduling model...")
            elif i < 90:
                status.info("Solving traffic flow model...")
            else:
                status.info("Finalizing results...")
            
            if i == 100:
                status.success("Optimization completed successfully!")
    
    # Results overview
    st.markdown("---")
    st.subheader("Optimization Results Overview")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Objective Value", value="1245.8", delta="-123.4")
    
    with col2:
        st.metric(label="Scheduled Projects", value="10/12", delta="83%")
    
    with col3:
        st.metric(label="Traffic Impact", value="187 trains", delta="-45 trains")
    
    # Example log output
    st.markdown("---")
    st.subheader("Optimization Log")
    
    log_placeholder = st.empty()
    log_placeholder.code("""
    2023-10-15 14:32:45 - INFO - Loading problem from problem.xml in directory ./data...
    2023-10-15 14:32:46 - INFO - Solving scheduling model...
    2023-10-15 14:33:12 - INFO - Scheduling model solved successfully.
    2023-10-15 14:33:12 - INFO - Solving traffic flow model with capacity constraints...
    2023-10-15 14:33:45 - INFO - Traffic flow model solved successfully.
    2023-10-15 14:33:45 - INFO - Results written to ./output
    """)

# Schedule Viewer page
elif page == "Schedule Viewer":
    st.header("Schedule Viewer")
    
    # Load schedule data
    st.subheader("Project Schedule")
    
    # Example: Load schedule data
    schedule_df = None
    
    # Load from file option
    schedule_file = st.file_uploader("Upload Schedule XML", type=["xml"])
    
    if schedule_file:
        # Save to temp file and load
        with open("temp_schedule.xml", "wb") as f:
            f.write(schedule_file.getvalue())
        
        schedule_df = load_schedule_data("temp_schedule.xml")
    else:
        # Use dummy data for demonstration
        dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
        schedule_df = pd.DataFrame({
            'Project': ['P1', 'P1', 'P2', 'P2', 'P3'],
            'Project Description': ['Bridge Repair', 'Bridge Repair', 'Track Renewal', 'Track Renewal', 'Signaling Upgrade'],
            'Task': ['T1', 'T2', 'T1', 'T2', 'T1'],
            'Task Description': ['Preparation', 'Main Work', 'Removal', 'Installation', 'System Update'],
            'Instance': [0, 0, 0, 0, 0],
            'Start': [dates[0], dates[2], dates[1], dates[4], dates[6]],
            'End': [dates[2], dates[5], dates[4], dates[8], dates[9]],
            'Duration (hours)': [48, 72, 72, 96, 72]
        })
    
    if schedule_df is not None:
        # Display schedule data
        with st.expander("Schedule Data"):
            st.dataframe(schedule_df)
        
        # Create Gantt chart
        gantt_fig = create_gantt_chart(schedule_df)
        if gantt_fig:
            st.plotly_chart(gantt_fig, use_container_width=True)
        
        # Project filters
        st.markdown("---")
        st.subheader("Filters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_projects = st.multiselect(
                "Select Projects",
                options=schedule_df['Project'].unique(),
                default=schedule_df['Project'].unique()
            )
        
        with col2:
            date_range = st.date_input(
                "Date Range",
                value=(schedule_df['Start'].min().date(), schedule_df['End'].max().date()),
                min_value=schedule_df['Start'].min().date(),
                max_value=schedule_df['End'].max().date()
            )
        
        # Filter data based on selection
        filtered_df = schedule_df[schedule_df['Project'].isin(selected_projects)]
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            filtered_df = filtered_df[
                (filtered_df['Start'] >= start_datetime) & 
                (filtered_df['End'] <= end_datetime)
            ]
        
        # Create filtered Gantt chart
        if len(filtered_df) > 0:
            filtered_gantt = create_gantt_chart(filtered_df)
            if filtered_gantt:
                st.plotly_chart(filtered_gantt, use_container_width=True)
        else:
            st.warning("No data matches the selected filters.")

# Network Visualization page
elif page == "Network Visualization":
    st.header("Network Visualization")
    
    # Load network data
    st.subheader("Railway Network")
    
    # Load from file option
    col1, col2 = st.columns(2)
    
    with col1:
        network_file = st.file_uploader("Upload Network XML", type=["xml"])
    
    with col2:
        capacity_file = st.file_uploader("Upload Capacity Utilization XML", type=["xml"])
    
    # Load network data
    network = None
    if network_file:
        # Save to temp file and load
        with open("temp_network.xml", "wb") as f:
            f.write(network_file.getvalue())
        
        network = load_network_data("temp_network.xml")
    
    # Load capacity data
    capacity_df = None
    if capacity_file:
        # Save to temp file and load
        with open("temp_capacity.xml", "wb") as f:
            f.write(capacity_file.getvalue())
        
        capacity_df = load_capacity_data("temp_capacity.xml")
    
    # Create network visualization
    if network is None:
        # Create dummy network for demonstration
        network = Network()
        network.add_node('A', 'Station A', 0, 0)
        network.add_node('B', 'Station B', 1, 0)
        network.add_node('C', 'Station C', 0, 1)
        network.add_node('D', 'Station D', 1, 1)
        network.add_link('A_B', 'A', 'B', 10, 2, 10)
        network.add_link('A_C', 'A', 'C', 10, 1, 5)
        network.add_link('B_D', 'B', 'D', 10, 1, 5)
        network.add_link('C_D', 'C', 'D', 10, 2, 10)
        
        # Create dummy capacity data
        if capacity_df is None:
            capacity_data = [
                {'Link': 'A_B', 'Period': 0, 'Start': datetime.now(), 'Utilization': 0.8},
                {'Link': 'A_C', 'Period': 0, 'Start': datetime.now(), 'Utilization': 0.3},
                {'Link': 'B_D', 'Period': 0, 'Start': datetime.now(), 'Utilization': 0.5},
                {'Link': 'C_D', 'Period': 0, 'Start': datetime.now(), 'Utilization': 0.2}
            ]
            capacity_df = pd.DataFrame(capacity_data)
    
    network_fig = create_network_visualization(network, capacity_df)
    
    if network_fig:
        import plotly.graph_objects as go
        
        fig = go.Figure(data=network_fig['data'], layout=network_fig['layout'])
        st.plotly_chart(fig, use_container_width=True)
    
    # Display network statistics
    st.markdown("---")
    st.subheader("Network Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Nodes", value=len(network.nodes))
    
    with col2:
        st.metric(label="Links", value=len(network.links))
    
    with col3:
        if capacity_df is not None:
            avg_util = capacity_df['Utilization'].mean()
            st.metric(label="Average Utilization", value=f"{avg_util:.2%}")
        else:
            st.metric(label="Average Utilization", value="N/A")
    
    # Display capacity data
    if capacity_df is not None:
        st.markdown("---")
        st.subheader("Capacity Utilization Data")
        
        # Create a heatmap of capacity utilization
        if len(capacity_df) > 0:
            # Get unique links and periods
            links = capacity_df['Link'].unique()
            periods = sorted(capacity_df['Period'].unique())
            
            # Create a pivot table
            pivot_df = capacity_df.pivot_table(
                values='Utilization', 
                index='Link', 
                columns='Period', 
                aggfunc='mean'
            ).fillna(0)
            
            # Create heatmap
            fig = px.imshow(
                pivot_df,
                labels=dict(x="Time Period", y="Link", color="Utilization"),
                x=periods,
                y=links,
                color_continuous_scale='Viridis',
                title='Capacity Utilization Heatmap'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("View Capacity Data"):
            st.dataframe(capacity_df)

# Traffic Impact page
elif page == "Traffic Impact":
    st.header("Traffic Impact Analysis")
    
    # Load traffic impact data
    st.subheader("Traffic Impact")
    
    # Load from file option
    traffic_file = st.file_uploader("Upload Traffic Impact XML", type=["xml"])
    
    summary = None
    flows_df = None
    
    if traffic_file:
        # Save to temp file and load
        with open("temp_traffic.xml", "wb") as f:
            f.write(traffic_file.getvalue())
        
        summary, flows_df = load_traffic_impact("temp_traffic.xml")
    else:
        # Use dummy data for demonstration
        summary = {
            'cancelled': 187,
            'delayed': 54,
            'diverted': 112
        }
        
        # Create dummy flows data
        lines = ['G_S_RST1', 'S_G_RST1', 'G_M_RST1', 'M_G_RST1', 'G_HB_GT1']
        routes = ['normal', 'div_A_B', 'div_C_D']
        periods = [0, 1, 2]
        
        flows_data = []
        for line in lines:
            for route in routes:
                for period in periods:
                    flows_data.append({
                        'Line': line,
                        'Route': route,
                        'Period': period,
                        'Value': np.random.randint(1, 10)
                    })
        
        flows_df = pd.DataFrame(flows_data)
    
    # Create impact charts
    if summary:
        impact_pie, flows_bar = create_traffic_impact_chart(summary, flows_df)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(impact_pie, use_container_width=True)
            
            # Display summary metrics
            st.markdown("### Impact Summary")
            
            subcol1, subcol2, subcol3 = st.columns(3)
            
            with subcol1:
                st.metric(label="Cancelled Trains", value=int(summary['cancelled']))
            
            with subcol2:
                st.metric(label="Delayed Trains", value=int(summary['delayed']))
            
            with subcol3:
                st.metric(label="Diverted Trains", value=int(summary['diverted']))
        
        with col2:
            if flows_bar:
                st.plotly_chart(flows_bar, use_container_width=True)
    
    # Display traffic flow data
    st.markdown("---")
    st.subheader("Traffic Flow Data")
    
    if flows_df is not None:
        with st.expander("View Flow Data"):
            st.dataframe(flows_df)
        
        # Flow analysis
        st.markdown("### Flow Analysis by Train Type")
        
        if 'Line' in flows_df.columns:
            # Extract train type from line ID
            flows_df['Train Type'] = flows_df['Line'].str.extract(r'_(\w+)$')
            
            # Group by train type
            train_type_summary = flows_df.groupby('Train Type')['Value'].sum().reset_index()
            
            fig = px.pie(
                train_type_summary,
                values='Value',
                names='Train Type',
                title='Traffic Flow by Train Type',
                color='Train Type',
                color_discrete_map={
                    'RST1': 'blue',
                    'RST2': 'lightblue',
                    'GT1': 'green',
                    'GT2': 'lightgreen'
                }
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Flow comparison: normal vs diverted
            st.markdown("### Normal vs. Diverted Traffic")
            
            route_summary = flows_df.groupby(['Train Type', 'Route'])['Value'].sum().reset_index()
            
            fig = px.bar(
                route_summary,
                x='Train Type',
                y='Value',
                color='Route',
                barmode='group',
                title='Normal vs. Diverted Traffic by Train Type'
            )
            
            st.plotly_chart(fig, use_container_width=True)

# Run the dashboard
# To run: streamlit run src/visualization/dashboard.py