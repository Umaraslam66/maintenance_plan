# maintenance_data.py
import pandas as pd
import numpy as np
import os
import datetime
import xml.etree.ElementTree as ET

# Import network data functionality
from network_data import get_network_data, is_valid_link, get_all_links

def create_maintenance_data():
    """Create maintenance project data (TPÅ) for Swedish railway"""
    print("Creating maintenance project data...")
    
    # Get network data to validate links
    _, links_df = get_network_data()
    valid_links = links_df['link_id'].tolist()
    
    print(f"Network data loaded with {len(valid_links)} valid links")

    # Create sample maintenance projects
    projects = [
        # Western Main Line projects
        {
            'project_id': '214',
            'description': 'Switch change Vårgårda',
            'link': 'G_A',
            'earliest_start': 'v2410',
            'latest_end': 'v2426',
            'tasks': [
                {'task_id': '214_1', 'description': 'Preparatory work', 'duration_hr': 8, 'blocking_percentage': 50},
                {'task_id': '214_2', 'description': 'Main closure', 'duration_hr': 48, 'blocking_percentage': 100},
                {'task_id': '214_3', 'description': 'Follow-up work', 'duration_hr': 8, 'blocking_percentage': 50}
            ]
        },
        {
            'project_id': '180',
            'description': 'Töreboda bridge over the Göta Canal',
            'link': 'TEO_HD',
            'earliest_start': 'v2410',
            'latest_end': 'v2426',
            'tasks': [
                {'task_id': '180_1', 'description': 'Bridge replacement', 'duration_hr': 96, 'blocking_percentage': 100}
            ]
        },
        # Southern Main Line projects
        {
            'project_id': '526',
            'description': 'Hässleholm railway yard, catenary refurbishment',
            'link': 'HM_HÖ',
            'earliest_start': 'v2410',
            'latest_end': 'v2420',
            'tasks': [
                {'task_id': '526_1', 'description': 'Main closure', 'duration_hr': 72, 'blocking_percentage': 100}
            ]
        },
        {
            'project_id': '450',
            'description': 'Hässleholm railway yard, catenary refurbishment',
            'link': 'HM_HÖ',
            'earliest_start': 'v2410',
            'latest_end': 'v2449',
            'tasks': [
                {'task_id': '450_1', 'description': 'Service window', 'duration_hr': 6, 'blocking_percentage': 'esp', 'count': 6}
            ]
        },
        # West Coast Line projects
        {
            'project_id': '877',
            'description': 'Varberg-Hamra, double track, tunnel',
            'link': 'KB_VB',
            'earliest_start': 'v2410',
            'latest_end': 'v2444',
            'tasks': [
                {'task_id': '877_1', 'description': 'Main closure', 'duration_hr': 96, 'blocking_percentage': 100}
            ]
        },
        {
            'project_id': '880',
            'description': 'Varberg-Hamra, double track, tunnel',
            'link': 'VRÖ_TEO',
            'earliest_start': 'v2410',
            'latest_end': 'v2449',
            'tasks': [
                {'task_id': '880_1', 'description': 'Service window', 'duration_hr': 8, 'blocking_percentage': 50}
            ]
        },
        # Northern Sweden projects
        {
            'project_id': 'N001',
            'description': 'Catenary replacement Bräcke-Långsele',
            'link': 'BÄ_LSL',
            'earliest_start': 'v2410',
            'latest_end': 'v2435',
            'tasks': [
                {'task_id': 'N001_1', 'description': 'Traffic disruption (10-week total closure)', 'duration_hr': 24*7*10, 'blocking_percentage': 100}
            ]
        },
        {
            'project_id': 'N002',
            'description': 'Catenary replacement Bräcke-Långsele',
            'link': 'BÄ_LSL',
            'earliest_start': 'v2410',
            'latest_end': 'v2435',
            'tasks': [
                {'task_id': 'N002_1', 'description': 'Service window (daily 8-hour shifts)', 'duration_hr': 8, 'blocking_percentage': 100, 'count': 70}
            ]
        },
        {
            'project_id': 'N003',
            'description': 'Track work Hudiksvall-Sundsvall',
            'link': 'HD_SU',
            'earliest_start': 'v2410',
            'latest_end': 'v2435',
            'tasks': [
                {'task_id': 'N003_1', 'description': 'Service window (daily 6-hour shifts on weekdays)', 'duration_hr': 6, 'blocking_percentage': 100, 'count': 50}
            ]
        },
        {
            'project_id': 'N004',
            'description': 'Track work Boden-Gällivare',
            'link': 'BD_GV',
            'earliest_start': 'v2410',
            'latest_end': 'v2435',
            'tasks': [
                {'task_id': 'N004_1', 'description': 'Service window (daily 8-hour shifts)', 'duration_hr': 8, 'blocking_percentage': 100, 'count': 60}
            ]
        }
    ]
    
    # Validate links and filter out invalid projects
    valid_projects = []
    for project in projects:
        link = project['link']
        if link in valid_links:
            valid_projects.append(project)
        else:
            print(f"Warning: Project {project['project_id']} references invalid link {link}. Skipping.")
    
    print(f"Filtered to {len(valid_projects)} valid projects")
    
    # Create DataFrame with rows similar to the TPÅ coordination sheet format
    tpa_data = []
    
    # Create a simulated view of the TPÅ coordination sheet
    for project in valid_projects:
        for task in project['tasks']:
            row = {
                'TPÅ_ID': project['project_id'],
                'Beskrivning': project['description'],
                'Sträcka': project['link'],
                'Åtgärd': task['description'],
                'Startdatum': project['earliest_start'],
                'Slutdatum': project['latest_end'],
                'Tidslängd (timmar)': task['duration_hr']
            }
            
            # Add a field for blocking percentage
            if task['blocking_percentage'] == 'esp':
                row['Trafikpåverkan'] = 'Enkelspårsdrift'
            else:
                row['Trafikpåverkan'] = f"{task['blocking_percentage']}% kapacitetsminskning"
            
            # Handle repeated tasks
            if 'count' in task:
                row['Upprepningar'] = task['count']
            else:
                row['Upprepningar'] = 1
                
            # Add to dataframe rows
            tpa_data.append(row)
    
    # Create week columns (v2410 to v2449)
    weeks = [f'v24{week:02d}' for week in range(10, 50)]
    for week in weeks:
        for i, row in enumerate(tpa_data):
            # Mark schedule based on start/end dates and a pattern
            if row['Startdatum'] <= week <= row['Slutdatum']:
                if i % 4 == 0:  # First project of each type - schedule for odd weeks
                    if int(week[3:]) % 2 == 1:
                        tpa_data[i][week] = 'X'
                elif i % 4 == 1:  # Second project - schedule for even weeks
                    if int(week[3:]) % 2 == 0:
                        tpa_data[i][week] = 'X'
                elif i % 4 == 2:  # Third project - schedule for first week of month
                    if int(week[4:]) % 4 == 1:
                        tpa_data[i][week] = 'X'
                else:  # Fourth project - schedule for last week of month
                    if int(week[4:]) % 4 == 0:
                        tpa_data[i][week] = 'X'
    
    # Create DataFrame
    tpa_df = pd.DataFrame(tpa_data)
    
    # Save to Excel
    os.makedirs('data/input', exist_ok=True)
    tpa_df.to_excel('data/input/tpa_maintenance.xlsx', index=False)
    
    print(f"Maintenance data created and saved to data/input/tpa_maintenance.xlsx")
    
    # Create XML version for the projects
    create_project_xml(valid_projects)
    
    return tpa_df

def create_project_xml(projects):
    """Create a XML file for the projects following the format in the paper"""
    
    # Create XML content
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<problem>\n'
    
    # Add resources section
    xml_content += '  <resources>\n'
    xml_content += '    <resource id="crew1" name="Maintenance crew 1" />\n'
    xml_content += '    <resource id="crew2" name="Maintenance crew 2" />\n'
    xml_content += '    <resource id="equip1" name="Special equipment 1" />\n'
    xml_content += '  </resources>\n'
    
    # Add projects
    xml_content += '  <projects>\n'
    
    for project in projects:
        xml_content += f'    <project id="{project["project_id"]}" desc="{project["description"]}" earliestStart="{project["earliest_start"]}" latestEnd="{project["latest_end"]}">\n'
        
        # Add tasks for this project
        for task in project['tasks']:
            xml_content += f'      <task id="{task["task_id"]}" desc="{task["description"]}" durationHr="{task["duration_hr"]}"'
            
            # Add count if present
            if 'count' in task:
                xml_content += f' count="{task["count"]}"'
                
            # Close task opening tag
            xml_content += '>\n'
            
            # Add traffic blocking
            xml_content += f'        <traffic_blocking link="{project["link"]}" amount="'
            if task['blocking_percentage'] == 'esp':
                xml_content += 'esp'
            else:
                xml_content += f'{task["blocking_percentage"]}'
            xml_content += '" />\n'
            
            # Add resource requirements (example)
            xml_content += '        <requiredResources>\n'
            xml_content += '          <resource id="crew1" amount="1" />\n'
            if task['duration_hr'] > 24:  # For longer tasks, add more resources
                xml_content += '          <resource id="equip1" amount="1" />\n'
            xml_content += '        </requiredResources>\n'
            
            # Close task
            xml_content += '      </task>\n'
        
        # Close project
        xml_content += '    </project>\n'
    
    # Close projects section
    xml_content += '  </projects>\n'
    
    # Add params section with some basic settings
    xml_content += '  <params>\n'
    xml_content += '    <keyVal key="cp_block">1.0</keyVal>\n'
    xml_content += '    <keyVal key="cp_bs">0.5</keyVal>\n'
    xml_content += '    <keyVal key="*">10</keyVal>\n'
    xml_content += '    <keyVal key="RST">10</keyVal>\n'
    xml_content += '    <keyVal key="GT">5</keyVal>\n'
    xml_content += '    <keyVal key="RST">10</keyVal>\n'
    xml_content += '    <keyVal key="GT">5</keyVal>\n'
    xml_content += '    <keyVal key="RST">1.2</keyVal>\n'
    xml_content += '    <keyVal key="GT">1.5</keyVal>\n'
    xml_content += '  </params>\n'
    
    # Close problem tag
    xml_content += '</problem>'
    
    # Save XML file
    with open('data/processed/projects.xml', 'w') as f:
        f.write(xml_content)
    
    print(f"Project XML created and saved to data/processed/projects.xml")

if __name__ == "__main__":
    create_maintenance_data()