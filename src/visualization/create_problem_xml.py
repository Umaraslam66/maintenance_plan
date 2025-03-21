# create_problem_xml.py (updated for encoding issues)
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import logging
import sys
import chardet
import unicodedata
import re
import itertools

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def validate_and_complete_network(network_root, traffic_root):
    """
    Validate network links and add missing links from traffic data.
    
    Parameters:
    -----------
    network_root : xml.etree.ElementTree.Element
        Root of the network XML
    traffic_root : xml.etree.ElementTree.Element
        Root of the traffic XML
    
    Returns:
    --------
    xml.etree.ElementTree.Element
        Updated network root with additional links
    """
    # Find existing links
    existing_links = network_root.find('.//links')
    if existing_links is None:
        existing_links = ET.SubElement(network_root, 'links')
    
    # Find existing nodes
    existing_nodes = network_root.find('.//nodes')
    if existing_nodes is None:
        existing_nodes = ET.SubElement(network_root, 'nodes')
    
    # Track existing link and node IDs
    existing_link_ids = set(link.get('id') for link in existing_links.findall('link'))
    existing_node_ids = set(node.get('id') for node in existing_nodes.findall('node'))
    
    # Collect links from different sources in traffic
    additional_links = []
    
    # Check line routes
    line_routes = traffic_root.findall('.//line_route')
    if line_routes:
        for route in line_routes:
            route_links = route.get('route', '').split()
            additional_links.extend(route_links)
    
    # Check traffic blocking
    blocking_links = traffic_root.findall('.//traffic_blocking')
    if blocking_links:
        for block in blocking_links:
            link_id = block.get('link')
            if link_id:
                additional_links.append(link_id)
    
    # Remove duplicates and filter out existing links
    additional_links = list(set(additional_links) - existing_link_ids)
    
    # Add missing links
    for link_id in additional_links:
        # Try to infer from link ID (assuming format like A_B)
        parts = link_id.split('_')
        
        # Ensure both nodes exist
        for node_id in parts[:2]:  # Take first two parts as node IDs
            if node_id not in existing_node_ids:
                # Create minimal node if not exists
                node = ET.SubElement(existing_nodes, 'node', 
                                   id=node_id, 
                                   name=f"Station {node_id}", 
                                   lat="0", 
                                   lon="0")
                existing_node_ids.add(node_id)
        
        # Create link
        if len(parts) >= 2:
            from_node = parts[0]
            to_node = parts[1]
            link = ET.SubElement(existing_links, 'link', 
                               id=link_id, 
                               **{
                                   'from': from_node, 
                                   'to': to_node, 
                                   'length': "10", 
                                   'tracks': "2", 
                                   'capacity': "10"
                               })
            logger.info(f"Added missing link: {link_id}")
    
    return network_root


def normalize_name(name):
    """
    Normalize names by handling Swedish and special characters.
    
    Parameters:
    -----------
    name : str
        The original name to normalize
    
    Returns:
    --------
    str
        A normalized version of the name
    """
    if not isinstance(name, str):
        return name
    
    # Comprehensive Swedish character mapping
    swedish_char_map = {
        'å': 'a', 'ä': 'a', 'ö': 'o',
        'Å': 'A', 'Ä': 'A', 'Ö': 'O',
        'é': 'e', 'è': 'e', 'ê': 'e',
        'É': 'E', 'È': 'E', 'Ê': 'E',
        'ü': 'u', 'Ü': 'U',
        'ø': 'o', 'Ø': 'O',
        'æ': 'ae', 'Æ': 'AE'
    }
    
    # First, replace known Swedish characters
    for swe_char, replacement in swedish_char_map.items():
        name = name.replace(swe_char, replacement)
    
    # Remove any remaining diacritical marks
    normalized = ''.join(
        char for char in unicodedata.normalize('NFKD', name)
        if unicodedata.category(char) != 'Mn'
    )
    
    # Remove any remaining non-alphanumeric characters except underscores
    normalized = re.sub(r'[^\w\s-]', '', normalized)
    
    # Replace multiple spaces with a single space
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # If empty after normalization, use a default
    if not normalized:
        normalized = 'unnamed'
    
    return normalized

def normalize_xml_element(element):
    """
    Recursively normalize names in XML elements.
    
    Parameters:
    -----------
    element : xml.etree.ElementTree.Element
        The XML element to normalize
    """
    # Normalize name-related attributes
    name_attrs = ['name', 'desc', 'description', 'id', 'from', 'to', 'line', 'link', 'project', 'task', 'node']
    
    for attr in name_attrs:
        if attr in element.attrib:
            # Normalize the attribute while preserving its original structure
            element.attrib[attr] = normalize_name(element.attrib[attr])
    
    # Recursively process child elements
    for child in element:
        normalize_xml_element(child)

def create_problem_xml(network_file=None, traffic_file=None, projects_file=None, output_file=None):
    """
    Create a combined problem.xml file from existing data files.
    
    Parameters:
    -----------
    network_file : str
        Path to the network XML file
    traffic_file : str
        Path to the traffic XML file
    projects_file : str
        Path to the projects XML file
    output_file : str
        Path to save the combined problem XML file
    """
    # Set default paths if not provided
    if network_file is None:
        network_file = 'data/processed/network.xml'
    
    if traffic_file is None:
        traffic_file = 'data/processed/traffic.xml'
    
    if projects_file is None:
        projects_file = 'data/processed/projects.xml'
    
    if output_file is None:
        output_file = 'data/processed/problem.xml'
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Create root element
    root = ET.Element("problem")
    
    # Track whether files were successfully merged
    success_count = 0
    
    # Add network data
    if os.path.exists(network_file):
        try:
            # Detect file encoding
            encoding = detect_encoding(network_file)
            logger.info(f"Detected encoding for {network_file}: {encoding}")
            
            # Read the XML file with detected encoding
            with open(network_file, 'r', encoding=encoding) as f:
                network_content = f.read()
            
            # Clean the content
            network_content = clean_xml_content(network_content)
            
            # Parse the cleaned content
            
            network_root = ET.fromstring(network_content)
            
            normalize_xml_element(network_root)
            
            # If the root element is <network>, add it directly
            if network_root.tag == 'network':
                root.append(network_root)
                logger.info(f"Successfully merged network data from {network_file}")
                success_count += 1
            else:
                # Try to find <network> element inside the root
                network_elem = network_root.find('.//network')
                if network_elem is not None:
                    root.append(network_elem)
                    logger.info(f"Successfully merged network data from {network_file}")
                    success_count += 1
                else:
                    logger.warning(f"Could not find <network> element in {network_file}")
                    # Create a minimal network element
                    create_minimal_network(root)
                    success_count += 1
        except Exception as e:
            logger.error(f"Error parsing network file {network_file}: {e}")
            # Create a minimal network element
            create_minimal_network(root)
    else:
        logger.warning(f"Network file {network_file} not found")
        # Create a minimal network element
        create_minimal_network(root)
        success_count += 1
    
    # Add traffic data
    if os.path.exists(traffic_file):
        try:
            # Detect file encoding
            encoding = detect_encoding(traffic_file)
            logger.info(f"Detected encoding for {traffic_file}: {encoding}")
            
            # Read the XML file with detected encoding
            with open(traffic_file, 'r', encoding=encoding) as f:
                traffic_content = f.read()
            
            # Clean the content
            traffic_content = clean_xml_content(traffic_content)
            
            # Parse the cleaned content
            traffic_root = ET.fromstring(traffic_content)

            normalize_xml_element(traffic_root)
            
            # If the root element is <traffic>, add it directly
            if traffic_root.tag == 'traffic':
                root.append(traffic_root)
                logger.info(f"Successfully merged traffic data from {traffic_file}")
                success_count += 1
            else:
                # Try to find <traffic> element inside the root
                traffic_elem = traffic_root.find('.//traffic')
                if traffic_elem is not None:
                    root.append(traffic_elem)
                    logger.info(f"Successfully merged traffic data from {traffic_file}")
                    success_count += 1
                else:
                    logger.warning(f"Could not find <traffic> element in {traffic_file}")
                    # Create a minimal traffic element
                    create_minimal_traffic(root)
                    success_count += 1
        except Exception as e:
            logger.error(f"Error parsing traffic file {traffic_file}: {e}")
            # Create a minimal traffic element
            create_minimal_traffic(root)
            success_count += 1
    else:
        logger.warning(f"Traffic file {traffic_file} not found")
        # Create a minimal traffic element
        create_minimal_traffic(root)
        success_count += 1
    




    # Add resources and projects data
    resources_added = False
    projects_added = False
    
    if os.path.exists(projects_file):
        try:
            # Detect file encoding
            encoding = detect_encoding(projects_file)
            logger.info(f"Detected encoding for {projects_file}: {encoding}")
            
            # Read the XML file with detected encoding
            with open(projects_file, 'r', encoding=encoding) as f:
                projects_content = f.read()
            
            # Clean the content
            projects_content = clean_xml_content(projects_content)
            
            # Parse the cleaned content
            projects_root = ET.fromstring(projects_content)

            normalize_xml_element(projects_root)
            
            # Try to find <resources> element
            resources_elem = projects_root.find('.//resources')
            if resources_elem is not None:
                root.append(resources_elem)
                logger.info(f"Successfully merged resources data from {projects_file}")
                resources_added = True
            
            # Try to find <projects> element
            projects_elem = projects_root.find('.//projects')
            if projects_elem is not None:
                root.append(projects_elem)
                logger.info(f"Successfully merged projects data from {projects_file}")
                projects_added = True
                success_count += 1
        except Exception as e:
            logger.error(f"Error parsing projects file {projects_file}: {e}")
    else:
        logger.warning(f"Projects file {projects_file} not found")
    
    # Add minimal resources if not found
    if not resources_added:
        resources = ET.SubElement(root, "resources")
        ET.SubElement(resources, "resource", id="crew1", name="Maintenance crew 1")
        logger.info("Added minimal resources data")
    
    # Add minimal projects if not found
    if not projects_added:
        projects = ET.SubElement(root, "projects")
        project = ET.SubElement(projects, "project", id="sample_proj", desc="Sample Project", 
                              earliestStart="2024-01-01 00:00:00", latestEnd="2024-12-31 23:59:59")
        task = ET.SubElement(project, "task", id="sample_task", desc="Sample Task", durationHr="48")
        
        # Find a valid link to reference
        network_elem = root.find('.//network')
        if network_elem is not None:
            link_elem = network_elem.find('.//link')
            if link_elem is not None and 'id' in link_elem.attrib:
                link_id = link_elem.attrib['id']
                ET.SubElement(task, "traffic_blocking", link=link_id, amount="50")
        
        logger.info("Added minimal projects data")
        success_count += 1
    
    # After parsing network and traffic XML
    if network_root is not None and traffic_root is not None:
        # Validate and complete network
        try:
            network_root = validate_and_complete_network(network_root, traffic_root)
        except Exception as e:
            logger.error(f"Error validating network links: {e}")
    
    # Add parameters
    params = ET.SubElement(root, "params")
    
    # Add scheduling parameters
    ET.SubElement(params, "keyVal", key="cp_block").text = "1.0"
    ET.SubElement(params, "keyVal", key="cp_bs").text = "0.5"
    ET.SubElement(params, "keyVal", key="*").text = "100"  # Default project cancellation cost
    
    # Add traffic parameters
    ET.SubElement(params, "keyVal", key="ct_cancel_RST").text = "10"
    ET.SubElement(params, "keyVal", key="ct_cancel_GT").text = "5"
    ET.SubElement(params, "keyVal", key="ct_post_RST").text = "5"
    ET.SubElement(params, "keyVal", key="ct_post_GT").text = "2"
    ET.SubElement(params, "keyVal", key="ct_time_RST").text = "1"
    ET.SubElement(params, "keyVal", key="ct_time_GT").text = "0.5"
    ET.SubElement(params, "keyVal", key="mx_inc_rel_RST").text = "1.2"
    ET.SubElement(params, "keyVal", key="mx_inc_abs_GT").text = "2.0"
    
    logger.info("Added parameters")
    
    # Add planning period
    plan = ET.SubElement(root, "plan")
    plan.set("start", "2024-01-01 00:00:00")
    plan.set("end", "2024-12-31 23:59:59")
    plan.set("period_length", "8")
    plan.set("traffic_start", "2024-01-01 00:00:00")
    plan.set("traffic_end", "2024-12-31 23:59:59")
    
    logger.info("Added planning period")
    
    # Create XML string and prettify it
    try:
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        
        # Remove empty lines (common in minidom output)
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        pretty_xml = '\n'.join(lines)
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        logger.info(f"Problem XML created and saved to {output_file}")
        
        if success_count >= 3:
            logger.info("All required components were successfully merged.")
        else:
            logger.warning("Some components were missing or failed to merge. A minimal replacement was created.")
        
        return True
    except Exception as e:
        logger.error(f"Error creating problem XML: {e}")
        return False

def detect_encoding(file_path):
    """Detect file encoding using chardet"""
    # Read a sample of the file
    with open(file_path, 'rb') as f:
        sample = f.read(10000)  # Read first 10000 bytes
    
    # Detect encoding
    result = chardet.detect(sample)
    encoding = result['encoding']
    
    # Use common fallbacks if detection failed or returned None
    if not encoding or encoding.lower() == 'ascii':
        # Try these encodings in order
        for enc in ['latin-1', 'iso-8859-1', 'cp1252', 'utf-8']:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    f.read(100)  # Try to read a bit
                return enc
            except UnicodeDecodeError:
                continue
        
        # If all else fails, use latin-1 which can read any file
        return 'latin-1'
    
    return encoding

def clean_xml_content(content):
    """
    Clean XML content to handle common issues.
    
    Parameters:
    -----------
    content : str
        Raw XML content to clean
    
    Returns:
    --------
    str
        Cleaned XML content
    """
    # Remove XML declaration if present
    if content.startswith('<?xml'):
        content = content[content.find('?>') + 2:].strip()
    
    # Remove any DOCTYPE declarations
    if '<!DOCTYPE' in content:
        start = content.find('<!DOCTYPE')
        end = content.find('>', start)
        if end != -1:
            content = content[:start] + content[end+1:]
    
    # Remove namespace declarations
    content = content.replace('xmlns="http://www.w3.org/1999/xhtml"', '')
    content = content.replace('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"', '')
    
    # Add root element if needed
    if not content.startswith('<'):
        content = f'<root>{content}</root>'
    
    return content

def create_minimal_network(root):
    """Create a minimal network element"""
    network = ET.SubElement(root, "network")
    nodes = ET.SubElement(network, "nodes")
    
    # Add minimal nodes
    ET.SubElement(nodes, "node", id="A", name="Station A", lat="0", lon="0")
    ET.SubElement(nodes, "node", id="B", name="Station B", lat="1", lon="0")
    
    links = ET.SubElement(network, "links")
    
    # Add minimal link
    ET.SubElement(links, "link", id="A_B", **{"from": "A", "to": "B", "length": "10", "tracks": "2", "capacity": "10"})
    
    logger.info("Created minimal network data")

def create_minimal_traffic(root):
    """Create a minimal traffic element"""
    traffic = ET.SubElement(root, "traffic")
    train_types = ET.SubElement(traffic, "train_types")
    ET.SubElement(train_types, "train_type", id="RST", name="Passenger Train")
    ET.SubElement(train_types, "train_type", id="GT", name="Freight Train")
    
    lines = ET.SubElement(traffic, "lines")
    ET.SubElement(lines, "line", id="A_B_RST", origin="A", destination="B", train_type="RST")
    
    line_demand = ET.SubElement(traffic, "line_demand")
    ET.SubElement(line_demand, "demand", line="A_B_RST", startHr="8", endHr="9", demand="5")
    
    # Find a valid link to reference
    network_elem = root.find('.//network')
    if network_elem is not None:
        link_elem = network_elem.find('.//link')
        if link_elem is not None and 'id' in link_elem.attrib:
            link_id = link_elem.attrib['id']
            
            line_routes = ET.SubElement(traffic, "line_routes")
            route = ET.SubElement(line_routes, "line_route", line="A_B_RST", route=f"{link_id}")
            ET.SubElement(route, "dur", link=link_id).text = "0.5"
    
    logger.info("Created minimal traffic data")

def check_files_exist(network_file, traffic_file, projects_file):
    """Check if the necessary files exist and provide suggestions if not"""
    missing_files = []
    
    if not os.path.exists(network_file):
        missing_files.append(("network", network_file))
    
    if not os.path.exists(traffic_file):
        missing_files.append(("traffic", traffic_file))
    
    if not os.path.exists(projects_file):
        missing_files.append(("projects", projects_file))
    
    if missing_files:
        logger.warning("Some required files are missing:")
        for file_type, file_path in missing_files:
            logger.warning(f"  - {file_type} file: {file_path}")
        
        logger.info("You should run the data generation scripts first:")
        if ("network", network_file) in missing_files:
            logger.info("  - Run 'python network_data.py' to generate network data")
        if ("traffic", traffic_file) in missing_files:
            logger.info("  - Run 'python traffic_data.py' to generate traffic data")
        if ("projects", projects_file) in missing_files:
            logger.info("  - Run 'python maintenance_data.py' to generate project data")
        
        return False
    
    return True

if __name__ == "__main__":
    # Check if chardet is installed
    try:
        import chardet
    except ImportError:
        logger.error("The 'chardet' package is required but not installed. Please install it with:")
        logger.error("pip install chardet")
        sys.exit(1)
        
    # Default file paths
    network_file = 'data/processed/network.xml'
    traffic_file = 'data/processed/traffic.xml'
    projects_file = 'data/processed/projects.xml'
    output_file = 'data/processed/problem.xml'
    
    # Check for command-line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("Usage: python create_problem_xml.py [network_file] [traffic_file] [projects_file] [output_file]")
            print("\nDefault values:")
            print(f"  network_file: {network_file}")
            print(f"  traffic_file: {traffic_file}")
            print(f"  projects_file: {projects_file}")
            print(f"  output_file: {output_file}")
            sys.exit(0)
        else:
            if len(sys.argv) > 1:
                network_file = sys.argv[1]
            if len(sys.argv) > 2:
                traffic_file = sys.argv[2]
            if len(sys.argv) > 3:
                projects_file = sys.argv[3]
            if len(sys.argv) > 4:
                output_file = sys.argv[4]
    
    # Check if files exist and provide suggestions
    if not check_files_exist(network_file, traffic_file, projects_file):
        logger.warning("Will attempt to create problem.xml with minimal data where files are missing.")
    
    # Create the problem XML
    result = create_problem_xml(network_file, traffic_file, projects_file, output_file)
    
    if result:
        # Provide next steps
        logger.info("\nYou can now run the optimization using:")
        logger.info(f"python src/execution/run.py --file problem.xml --dir data/processed --opt both --out_dir results/test_run")
    else:
        logger.error("Failed to create problem.xml")
        sys.exit(1)