import os
import xml.dom.minidom as md
import random
from datetime import datetime, timedelta

def create_directories():
    os.makedirs("data/processed", exist_ok=True)
    return "data/processed"

def generate_network_xml(output_dir):
    """Generate a simple, valid network XML file"""
    doc = md.getDOMImplementation().createDocument(None, "network", None)
    root = doc.documentElement
    
    # Create nodes section
    nodes = doc.createElement("nodes")
    root.appendChild(nodes)
    
    # Add some nodes
    for i in range(1, 6):
        node = doc.createElement("node")
        node.setAttribute("id", f"N{i}")
        node.setAttribute("name", f"Station {i}")
        node.setAttribute("lat", str(59 + i/10))
        node.setAttribute("lon", str(18 + i/10))
        node.setAttribute("merge_group", "Group1")
        nodes.appendChild(node)
    
    # Create links section
    links = doc.createElement("links")
    root.appendChild(links)
    
    # Add some links
    for i in range(1, 5):
        link = doc.createElement("link")
        link.setAttribute("id", f"L{i}")
        link.setAttribute("from", f"N{i}")
        link.setAttribute("to", f"N{i+1}")
        link.setAttribute("length", str(10 + i))
        link.setAttribute("tracks", str(1 + (i % 2)))
        link.setAttribute("capacity", str(5 + i))
        links.appendChild(link)
    
    # Save to file
    with open(os.path.join(output_dir, "network.xml"), "w") as f:
        f.write(doc.toprettyxml())
    
    return os.path.join(output_dir, "network.xml")

def generate_projects_xml(output_dir):
    """Generate a simple, valid projects XML file"""
    doc = md.getDOMImplementation().createDocument(None, "data", None)
    root = doc.documentElement
    
    # Create projects section
    projects = doc.createElement("projects")
    root.appendChild(projects)
    
    # Add some projects
    for i in range(1, 4):
        project = doc.createElement("project")
        project.setAttribute("id", f"P{i}")
        project.setAttribute("desc", f"Project {i}")
        project.setAttribute("earliestStart", f"2024-0{i}-01")
        project.setAttribute("latestEnd", f"2024-{i+3}-01")
        projects.appendChild(project)
        
        # Add tasks to each project
        for j in range(1, 3):
            task = doc.createElement("task")
            task.setAttribute("id", f"T{j}")
            task.setAttribute("desc", f"Task {j} of Project {i}")
            task.setAttribute("durationHr", str(24 * (i + j)))
            task.setAttribute("count", "1")
            project.appendChild(task)
            
            # Add traffic blocking
            blocking = doc.createElement("traffic_blocking")
            blocking.setAttribute("link", f"L{j}")
            blocking.setAttribute("amount", str(50 if j == 1 else "100"))
            task.appendChild(blocking)
            
            # Add required resources
            resources = doc.createElement("requiredResources")
            task.appendChild(resources)
            
            resource = doc.createElement("resource")
            resource.setAttribute("id", f"R{j}")
            resource.setAttribute("amount", "1")
            resources.appendChild(resource)
    
    # Save to file
    with open(os.path.join(output_dir, "projects.xml"), "w") as f:
        f.write(doc.toprettyxml())
    
    return os.path.join(output_dir, "projects.xml")

def generate_traffic_xml(output_dir):
    """Generate a simple, valid traffic XML file"""
    doc = md.getDOMImplementation().createDocument(None, "traffic", None)
    root = doc.documentElement
    
    # Add train types
    train_types = doc.createElement("train_types")
    root.appendChild(train_types)
    
    for i, type_name in enumerate(["Passenger", "Freight", "Express"]):
        tt = doc.createElement("train_type")
        tt.setAttribute("id", f"TT{i+1}")
        tt.setAttribute("name", type_name)
        train_types.appendChild(tt)
    
    # Add lines
    lines = doc.createElement("lines")
    root.appendChild(lines)
    
    for i in range(1, 4):
        line = doc.createElement("line")
        line.setAttribute("id", f"Line{i}")
        line.setAttribute("origin", f"N1")
        line.setAttribute("destination", f"N{i+2}")
        line.setAttribute("train_type", f"TT{i}")
        lines.appendChild(line)
    
    # Add demand
    demand = doc.createElement("demand")
    root.appendChild(demand)
    
    for i in range(1, 4):
        d = doc.createElement("demand")
        d.setAttribute("line", f"Line{i}")
        d.setAttribute("startHr", "0")
        d.setAttribute("endHr", "24")
        d.setAttribute("demand", str(10 * i))
        demand.appendChild(d)
    
    # Add routes
    routes = doc.createElement("routes")
    root.appendChild(routes)
    
    for i in range(1, 4):
        route = doc.createElement("line_route")
        route.setAttribute("line", f"Line{i}")
        route.setAttribute("route", f"N1-N2-N{i+2}")
        routes.appendChild(route)
        
        # Duration for each link
        for j in range(1, 3):
            dur = doc.createElement("dur")
            dur.setAttribute("link", f"L{j}")
            dur.appendChild(doc.createTextNode("30"))
            route.appendChild(dur)
    
    # Save to file
    with open(os.path.join(output_dir, "traffic.xml"), "w") as f:
        f.write(doc.toprettyxml())
    
    return os.path.join(output_dir, "traffic.xml")

def generate_problem_xml(output_dir, network_file, projects_file, traffic_file):
    """Generate a consolidated problem XML file"""
    doc = md.getDOMImplementation().createDocument(None, "problem", None)
    root = doc.documentElement
    
    # Add references to other files
    plan = doc.createElement("plan")
    plan.setAttribute("start", "2024-01-01 00:00:00")
    plan.setAttribute("end", "2024-12-31 23:59:59")
    plan.setAttribute("period_length", "8")
    plan.setAttribute("traffic_start", "2024-01-01 00:00:00")
    plan.setAttribute("traffic_end", "2024-12-31 23:59:59")
    root.appendChild(plan)
    
    # Save to file
    with open(os.path.join(output_dir, "problem.xml"), "w") as f:
        f.write(doc.toprettyxml())
        f.write(f"<!-- Network: {network_file} -->\n")
        f.write(f"<!-- Projects: {projects_file} -->\n")
        f.write(f"<!-- Traffic: {traffic_file} -->\n")
    
    return os.path.join(output_dir, "problem.xml")

def main():
    output_dir = create_directories()
    print(f"Generating XML files in {output_dir}")
    
    network_file = generate_network_xml(output_dir)
    print(f"Generated network file: {network_file}")
    
    projects_file = generate_projects_xml(output_dir)
    print(f"Generated projects file: {projects_file}")
    
    traffic_file = generate_traffic_xml(output_dir)
    print(f"Generated traffic file: {traffic_file}")
    
    problem_file = generate_problem_xml(output_dir, network_file, projects_file, traffic_file)
    print(f"Generated problem file: {problem_file}")
    
    print("\nAll files generated successfully!")
    print("You can now generate the complete dataset in the Railway Planning Dashboard.")

if __name__ == "__main__":
    main()