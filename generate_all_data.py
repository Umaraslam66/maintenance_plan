# generate_all_data.py
import os
import sys
import time

def generate_all_data():
    """
    Generate all data for the SATT-BP system in the correct order:
    1. Network data
    2. Maintenance data
    3. Traffic data
    
    This ensures consistency across all data files.
    """
    print("="*80)
    print("SATT-BP Data Generation Process")
    print("="*80)
    
    # Create necessary directories
    os.makedirs('data/input', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)
    
    # Step 1: Generate network data
    print("\nStep 1: Generating network data...")
    try:
        from src.visualization.network_data import create_network_data
        stations_df, links_df = create_network_data()
        print(f"Successfully generated network data with {len(stations_df)} nodes and {len(links_df)} links")
        print("Network data saved to data/input/stations.xlsx, data/input/links.xlsx, and data/processed/network.xml")
    except Exception as e:
        print(f"Error generating network data: {e}")
        sys.exit(1)
    
    time.sleep(1)  # Pause for readability
    
    # Step 2: Generate maintenance data
    print("\nStep 2: Generating maintenance data...")
    try:
        from src.visualization.maintenance_data import create_maintenance_data
        maintenance_df = create_maintenance_data()
        print(f"Successfully generated maintenance data with {len(maintenance_df)} maintenance activities")
        print("Maintenance data saved to data/input/tpa_maintenance.xlsx and data/processed/projects.xml")
    except Exception as e:
        print(f"Error generating maintenance data: {e}")
        sys.exit(1)
    
    time.sleep(1)  # Pause for readability
    
    # Step 3: Generate traffic data
    print("\nStep 3: Generating traffic data...")
    try:
        from src.visualization.traffic_data import create_traffic_data
        relations_df, schedule_df, demand_df, link_times_df = create_traffic_data()
        print(f"Successfully generated traffic data:")
        print(f"- {len(relations_df)} train relations")
        print(f"- {len(schedule_df)} train schedule entries")
        print(f"- {len(demand_df)} demand entries")
        print(f"- {len(link_times_df)} link travel time entries")
        print("Traffic data saved to data/input/*.xlsx and data/processed/traffic.xml")
    except Exception as e:
        print(f"Error generating traffic data: {e}")
        sys.exit(1)
    
    # Step 4: Create consolidated problem.xml
    print("\nStep 4: Creating consolidated problem.xml...")
    try:
        from src.visualization.create_problem_xml import create_problem_xml
        create_problem_xml(
            network_file='data/processed/network.xml',
            traffic_file='data/processed/traffic.xml',
            projects_file='data/processed/projects.xml'
        )
        print("Successfully created consolidated problem.xml")
    except Exception as e:
        print(f"Error creating problem.xml: {e}")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("Data Generation Complete")
    print("="*80)
    print("\nYou can now run the optimization using:")
    print("python src/execution/run.py --file problem.xml --dir data/processed --opt both --out_dir results/test_run")

if __name__ == "__main__":
    generate_all_data()