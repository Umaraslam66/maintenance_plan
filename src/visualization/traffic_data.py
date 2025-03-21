# traffic_data.py
import pandas as pd
import numpy as np
import os
import datetime

# Import network data functionality
from network_data import get_network_data, is_valid_node, is_valid_link, validate_route

def create_traffic_data():
    """Create traffic data for Swedish railway network"""
    print("Creating traffic data for Swedish railway network...")
    
    # Get network data to validate nodes and links
    stations_df, links_df = get_network_data()
    valid_nodes = stations_df['node_id'].tolist()
    valid_links = links_df['link_id'].tolist()
    
    print(f"Network data loaded with {len(valid_nodes)} valid nodes and {len(valid_links)} valid links")
    
    # Define train types
    train_types = ['RST', 'GT']  # Passenger and Freight
    
    # Create some sample train relations based on the network
    relations = [
        # Main passenger routes
        {'line': 'G_S_RST1', 'origin': 'G', 'destination': 'S', 'train_type': 'RST', 'route': 'G-A-SK-HB-NR-LI-S', 'run_time_hr': 3.5},
        {'line': 'S_G_RST1', 'origin': 'S', 'destination': 'G', 'train_type': 'RST', 'route': 'S-LI-NR-HB-SK-A-G', 'run_time_hr': 3.5},
        {'line': 'G_M_RST1', 'origin': 'G', 'destination': 'M', 'train_type': 'RST', 'route': 'G-KB-VB-VRÖ-HPBG-D-HM-HÖ-E-LU-M', 'run_time_hr': 4.2},
        {'line': 'M_G_RST1', 'origin': 'M', 'destination': 'G', 'train_type': 'RST', 'route': 'M-LU-E-HÖ-HM-D-HPBG-VRÖ-VB-KB-G', 'run_time_hr': 4.2},
        
        # Regional passenger services
        {'line': 'G_HB_RST2', 'origin': 'G', 'destination': 'HB', 'train_type': 'RST', 'route': 'G-A-SK-HB', 'run_time_hr': 2.0},
        {'line': 'HB_G_RST2', 'origin': 'HB', 'destination': 'G', 'train_type': 'RST', 'route': 'HB-SK-A-G', 'run_time_hr': 2.0},
        {'line': 'HM_LU_RST2', 'origin': 'HM', 'destination': 'LU', 'train_type': 'RST', 'route': 'HM-HÖ-E-LU', 'run_time_hr': 1.0},
        {'line': 'LU_HM_RST2', 'origin': 'LU', 'destination': 'HM', 'train_type': 'RST', 'route': 'LU-E-HÖ-HM', 'run_time_hr': 1.0},
        
        # Freight routes
        {'line': 'G_HB_GT1', 'origin': 'G', 'destination': 'HB', 'train_type': 'GT', 'route': 'G-A-SK-HB', 'run_time_hr': 3.0},
        {'line': 'HB_G_GT1', 'origin': 'HB', 'destination': 'G', 'train_type': 'GT', 'route': 'HB-SK-A-G', 'run_time_hr': 3.0},
        {'line': 'G_M_GT1', 'origin': 'G', 'destination': 'M', 'train_type': 'GT', 'route': 'G-KB-VB-VRÖ-HPBG-D-HM-HÖ-E-LU-M', 'run_time_hr': 6.0},
        {'line': 'M_G_GT1', 'origin': 'M', 'destination': 'G', 'train_type': 'GT', 'route': 'M-LU-E-HÖ-HM-D-HPBG-VRÖ-VB-KB-G', 'run_time_hr': 6.0},
        
        # Northern Sweden routes
        {'line': 'S_LY_RST1', 'origin': 'S', 'destination': 'LY', 'train_type': 'RST', 'route': 'S-LI-NR-HB-NK-AV-HM-SU-BÄ-LSL-VN-UÅ-BD-LY', 'run_time_hr': 12.0},
        {'line': 'LY_S_RST1', 'origin': 'LY', 'destination': 'S', 'train_type': 'RST', 'route': 'LY-BD-UÅ-VN-LSL-BÄ-SU-HM-AV-NK-HB-NR-LI-S', 'run_time_hr': 12.0},
        {'line': 'LY_KA_RST1', 'origin': 'LY', 'destination': 'KA', 'train_type': 'RST', 'route': 'LY-BD-GV-KA', 'run_time_hr': 4.0},
        {'line': 'KA_LY_RST1', 'origin': 'KA', 'destination': 'LY', 'train_type': 'RST', 'route': 'KA-GV-BD-LY', 'run_time_hr': 4.0},
        
        # ARE/NRE (Oslo-Narvik) freight train
        {'line': 'ARE_NRE_GT2', 'origin': 'S', 'destination': 'KA', 'train_type': 'GT', 'route': 'S-LI-NR-HB-NK-AV-HM-SU-BÄ-LSL-VN-UÅ-BD-GV-KA', 'run_time_hr': 20.0},
        {'line': 'NRE_ARE_GT2', 'origin': 'KA', 'destination': 'S', 'train_type': 'GT', 'route': 'KA-GV-BD-UÅ-VN-LSL-BÄ-SU-HM-AV-NK-HB-NR-LI-S', 'run_time_hr': 20.0},
        
        # Steel pendulum freight train (Luleå-Borlänge)
        {'line': 'LY_HB_GT2', 'origin': 'LY', 'destination': 'HB', 'train_type': 'GT', 'route': 'LY-BD-UÅ-VN-LSL-BÄ-SU-HM-AV-NK-HB', 'run_time_hr': 16.0},
        {'line': 'HB_LY_GT2', 'origin': 'HB', 'destination': 'LY', 'train_type': 'GT', 'route': 'HB-NK-AV-HM-SU-BÄ-LSL-VN-UÅ-BD-LY', 'run_time_hr': 16.0}
    ]
    
    # Filter and validate relations
    valid_relations = []
    
    for relation in relations:
        # Check if origin and destination nodes exist
        if not is_valid_node(relation['origin']):
            print(f"Warning: Route {relation['line']} has invalid origin node {relation['origin']}. Skipping.")
            continue
            
        if not is_valid_node(relation['destination']):
            print(f"Warning: Route {relation['line']} has invalid destination node {relation['destination']}. Skipping.")
            continue
        
        # Check if all nodes in route exist
        route_nodes = relation['route'].split('-')
        invalid_nodes = [node for node in route_nodes if not is_valid_node(node)]
        
        if invalid_nodes:
            print(f"Warning: Route {relation['line']} contains invalid nodes: {invalid_nodes}. Skipping.")
            continue
        
        # Check if route forms a valid path (all nodes are connected)
        is_valid, missing_links = validate_route(route_nodes)
        
        if not is_valid:
            print(f"Warning: Route {relation['line']} contains missing links: {missing_links}. Skipping.")
            continue
        
        # If we get here, the relation is valid
        valid_relations.append(relation)
    
    print(f"Filtered to {len(valid_relations)} valid relations out of {len(relations)} original relations")
    
    # Create a relations dataframe
    relations_df = pd.DataFrame(valid_relations)
    
    # Create train time table and daily volumes
    train_schedule = []
    
    # For each relation, create timetable entries
    for idx, relation in enumerate(valid_relations):
        # Parse route to get links
        nodes = relation['route'].split('-')
        links = []
        for i in range(len(nodes)-1):
            links.append(f"{nodes[i]}_{nodes[i+1]}")
        
        # Determine number of trains per day based on train type
        if relation['train_type'] == 'RST':
            if 'RST1' in relation['line']:  # Long-distance passenger
                num_trains_per_day = 6  # Every 4 hours during day
                start_hours = [5, 9, 13, 15, 17, 21]
            else:  # Regional passenger
                num_trains_per_day = 12  # Every 2 hours
                start_hours = [5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 1, 3]
        else:  # Freight
            if 'GT1' in relation['line']:  # Regular freight
                num_trains_per_day = 4  # A few per day
                start_hours = [2, 8, 14, 20]
            else:  # Special freight (ARE/NRE or Steel pendulum)
                num_trains_per_day = 2  # Usually 2 per day
                start_hours = [0, 12]
        
        # Create schedule entries
        for day in range(7):  # Monday to Sunday
            for hour_idx, start_hour in enumerate(start_hours[:num_trains_per_day]):
                train_id = f"{relation['line']}_{day}_{hour_idx}"
                
                # Calculate arrival time
                departure_time = datetime.datetime(2022, 1, 3 + day, start_hour, 0)
                arrival_time = departure_time + datetime.timedelta(hours=relation['run_time_hr'])
                
                # Add to schedule
                train_schedule.append({
                    'train_id': train_id,
                    'line': relation['line'],
                    'origin': relation['origin'],
                    'destination': relation['destination'],
                    'train_type': relation['train_type'],
                    'route': relation['route'],
                    'departure_time': departure_time,
                    'arrival_time': arrival_time,
                    'run_time_hr': relation['run_time_hr'],
                    'day_of_week': day
                })
    
    # Create a train schedule dataframe
    schedule_df = pd.DataFrame(train_schedule)
    
    # Create traffic demand data
    demand_data = []
    
    # Aggregate demand by line, start hour, and end hour
    for line in relations_df['line'].unique():
        line_schedule = schedule_df[schedule_df['line'] == line]
        
        # Group by hour of day to get hourly demand
        for hour in range(24):
            # Filter trains departing in this hour
            hour_schedule = line_schedule[line_schedule['departure_time'].dt.hour == hour]
            trains_in_hour = len(hour_schedule)
            
            if trains_in_hour > 0:
                demand_data.append({
                    'line': line,
                    'startHr': hour,
                    'endHr': hour + 1,
                    'demand': trains_in_hour
                })
    
    # Create demand dataframe
    demand_df = pd.DataFrame(demand_data)
    
    # Calculate link travel times for each line
    link_times = []
    
    for idx, relation in enumerate(valid_relations):
        # Parse route to get links
        nodes = relation['route'].split('-')
        
        # Calculate approximate travel time per link
        total_links = len(nodes) - 1
        avg_time_per_link = relation['run_time_hr'] / total_links
        
        for i in range(total_links):
            link_id = f"{nodes[i]}_{nodes[i+1]}"
            link_times.append({
                'line': relation['line'],
                'link': link_id,
                'duration': avg_time_per_link
            })
    
    # Create link times dataframe
    link_times_df = pd.DataFrame(link_times)
    
    # Save to Excel files
    os.makedirs('data/input', exist_ok=True)
    relations_df.to_excel('data/input/train_relations.xlsx', index=False)
    schedule_df.to_excel('data/input/train_schedule.xlsx', index=False)
    demand_df.to_excel('data/input/train_demand.xlsx', index=False)
    link_times_df.to_excel('data/input/link_travel_times.xlsx', index=False)
    
    print(f"Traffic data created and saved to data/input/ directory")
    
    # Also create a traffic XML version based on the format described in the paper
    create_traffic_xml(relations_df, schedule_df, demand_df, link_times_df)
    
    return relations_df, schedule_df, demand_df, link_times_df

def create_traffic_xml(relations_df, schedule_df, demand_df, link_times_df):
    """Create a XML file for the traffic data following the format in the paper"""
    
    # Create XML content
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<traffic>\n'
    
    # Add train types
    xml_content += '  <train_types>\n'
    xml_content += '    <train_type id="RST" name="Passenger Train"/>\n'
    xml_content += '    <train_type id="GT" name="Freight Train"/>\n'
    xml_content += '  </train_types>\n'
    
    # Add lines
    xml_content += '  <lines>\n'
    for _, relation in relations_df.iterrows():
        xml_content += f'    <line id="{relation["line"]}" origin="{relation["origin"]}" destination="{relation["destination"]}" train_type="{relation["train_type"]}"/>\n'
    xml_content += '  </lines>\n'
    
    # Add demand
    xml_content += '  <line_demand>\n'
    for _, demand in demand_df.iterrows():
        xml_content += f'    <demand line="{demand["line"]}" startHr="{demand["startHr"]}" endHr="{demand["endHr"]}" demand="{demand["demand"]}"/>\n'
    xml_content += '  </line_demand>\n'
    
    # Add route information
    xml_content += '  <line_routes>\n'
    for line in relations_df['line'].unique():
        line_data = relations_df[relations_df['line'] == line].iloc[0]
        xml_content += f'    <line_route line="{line}" route="{line_data["route"]}">\n'
        
        # Add link durations for this line
        line_link_times = link_times_df[link_times_df['line'] == line]
        for _, link_time in line_link_times.iterrows():
            xml_content += f'      <dur link="{link_time["link"]}">{link_time["duration"]}</dur>\n'
        
        xml_content += '    </line_route>\n'
    xml_content += '  </line_routes>\n'
    
    # Add individual trains (for illustration)
    xml_content += '  <trains>\n'
    for _, train in schedule_df.head(10).iterrows():  # Just include first 10 for brevity
        dep_time = train['departure_time'].strftime('%Y-%m-%d %H:%M:%S')
        arr_time = train['arrival_time'].strftime('%Y-%m-%d %H:%M:%S')
        xml_content += f'    <train id="{train["train_id"]}" line="{train["line"]}" departure="{dep_time}" arrival="{arr_time}"/>\n'
    xml_content += '  </trains>\n'
    
    # Add traffic year definition
    xml_content += '  <traffic_year>\n'
    xml_content += '    <period type="normal" startDate="2024-01-01" endDate="2024-12-31">\n'
    xml_content += '      <day weekday="0" dataDate="2022-01-03"/>\n'  # Monday
    xml_content += '      <day weekday="1" dataDate="2022-01-04"/>\n'  # Tuesday
    xml_content += '      <day weekday="2" dataDate="2022-01-05"/>\n'  # Wednesday
    xml_content += '      <day weekday="3" dataDate="2022-01-06"/>\n'  # Thursday
    xml_content += '      <day weekday="4" dataDate="2022-01-07"/>\n'  # Friday
    xml_content += '      <day weekday="5" dataDate="2022-01-08"/>\n'  # Saturday
    xml_content += '      <day weekday="6" dataDate="2022-01-09"/>\n'  # Sunday
    xml_content += '    </period>\n'
    xml_content += '    <period type="easter" startDate="2024-03-29" endDate="2024-04-01">\n'
    xml_content += '      <day weekday="4" dataDate="2022-04-14"/>\n'  # Good Friday
    xml_content += '      <day weekday="5" dataDate="2022-04-15"/>\n'  # Easter Saturday
    xml_content += '      <day weekday="6" dataDate="2022-04-16"/>\n'  # Easter Sunday
    xml_content += '      <day weekday="0" dataDate="2022-04-17"/>\n'  # Easter Monday
    xml_content += '    </period>\n'
    xml_content += '    <period type="summer" startDate="2024-07-15" endDate="2024-08-04">\n'
    xml_content += '      <day weekday="0" dataDate="2022-07-18"/>\n'  # Monday in summer
    xml_content += '      <day weekday="1" dataDate="2022-07-19"/>\n'  # Tuesday in summer
    xml_content += '      <day weekday="2" dataDate="2022-07-20"/>\n'  # Wednesday in summer
    xml_content += '      <day weekday="3" dataDate="2022-07-21"/>\n'  # Thursday in summer
    xml_content += '      <day weekday="4" dataDate="2022-07-22"/>\n'  # Friday in summer
    xml_content += '      <day weekday="5" dataDate="2022-07-23"/>\n'  # Saturday in summer
    xml_content += '      <day weekday="6" dataDate="2022-07-24"/>\n'  # Sunday in summer
    xml_content += '    </period>\n'
    xml_content += '  </traffic_year>\n'
    
    xml_content += '</traffic>'
    
    # Save XML file
    with open('data/processed/traffic.xml', 'w') as f:
        f.write(xml_content)
    
    print(f"Traffic XML created and saved to data/processed/traffic.xml")

if __name__ == "__main__":
    create_traffic_data()