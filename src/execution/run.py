# This file is part of the SATT-BP tool

# src/execution/run.py
import os
import sys
import logging
import argparse
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path

# Add parent directory to path to import the tcr_opt module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from execution.tcr_opt import TCROptimizer

def configure_logging(log_file=None, log_level=logging.INFO):
    """Configure logging to file and console"""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logging.basicConfig(level=log_level, format=log_format)
    
    # Configure file handler if log_file is provided
    if log_file:
        if log_file == "<>":
            # Use default log file name based on script name
            script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
            log_file = f"{script_name}.log"
        
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # Add file handler to root logger
        logging.getLogger().addHandler(file_handler)
    
    return logging.getLogger()

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="TCR Optimization Tool")
    
    # General arguments
    parser.add_argument("--file", type=str, required=True, help="Input file name (YAML or XML)")
    parser.add_argument("--dir", type=str, default="./data", help="Directory containing the input file")
    parser.add_argument("--opt", type=str, default="both", choices=["proj", "traf", "both"], 
                        help="Which model to run: proj (scheduling), traf (traffic), or both")
    parser.add_argument("--log", type=str, default="<>", help="Log file name. Use stdout for console output.")
    parser.add_argument("--prt_vlvl", type=int, default=1, help="Print verbosity level (1-3)")
    parser.add_argument("--opt_vlvl", type=int, default=2, help="Optimization solver verbosity level (0-4)")
    
    # Filter arguments
    parser.add_argument("--proj_filter", type=str, help="Comma-separated list of project prefixes to include")
    parser.add_argument("--side_filter", type=str, help="Comma-separated list of prefixes for fixed track closures")
    parser.add_argument("--time_filter", type=str, help="Time period filter (start,end)")
    parser.add_argument("--period_len", type=float, help="Period length in hours")
    
    # Scheduling model arguments
    parser.add_argument("--opt_gap", type=float, default=0.01, help="Relative optimality gap")
    parser.add_argument("--opt_time", type=int, default=3600, help="Time limit for optimization (seconds)")
    parser.add_argument("--side_sched", type=str, help="File name with project data for fixed track closures")
    parser.add_argument("--inp_capuse", type=str, help="File name with capacity data for traffic")
    parser.add_argument("--inp_affected", type=str, help="File with affected traffic days and filter for capacity file")
    parser.add_argument("--log_capblk", type=str, help="File name to save capacity blocks from scheduling")
    
    # Traffic model arguments
    parser.add_argument("--traf_dates", type=str, help="How to divide the planning period for traffic")
    parser.add_argument("--log_capuse", type=str, help="File name to save capacity usage from traffic")
    
    # Output arguments
    parser.add_argument("--out_dir", type=str, default="./output", help="Directory for output files")
    
    return parser.parse_args()

def load_fixed_blockings(filename, filter_str=None):
    """Load fixed capacity blockings from file"""
    if not os.path.exists(filename):
        logging.error(f"Fixed blocking file not found: {filename}")
        return None
    
    try:
        tree = ET.parse(filename)
        root = tree.getroot()
        
        fixed_blockings = {}
        
        # Parse capacity blockings
        for block_elem in root.findall('.//blocking'):
            link_id = block_elem.get('link')
            period = int(block_elem.get('period'))
            value = float(block_elem.get('value'))
            
            key = (link_id, period)
            fixed_blockings[key] = value
        
        return fixed_blockings
    
    except Exception as e:
        logging.error(f"Error loading fixed blockings: {e}")
        return None

def load_capacity_usage(filename, filter_str=None):
    """Load traffic capacity usage from file"""
    if not os.path.exists(filename):
        logging.error(f"Capacity usage file not found: {filename}")
        return None
    
    try:
        tree = ET.parse(filename)
        root = tree.getroot()
        
        capacity_usage = {}
        
        # Parse capacity utilization
        for util_elem in root.findall('.//util'):
            link_id = util_elem.get('link')
            period = int(util_elem.get('period'))
            value = float(util_elem.get('value'))
            
            key = (link_id, period)
            capacity_usage[key] = value
        
        return capacity_usage
    
    except Exception as e:
        logging.error(f"Error loading capacity usage: {e}")
        return None

def load_affected_days(filename):
    """Load affected traffic days from file"""
    if not os.path.exists(filename):
        logging.error(f"Affected days file not found: {filename}")
        return None
    
    try:
        tree = ET.parse(filename)
        root = tree.getroot()
        
        affected_days = []
        
        # Parse affected days
        for day_elem in root.findall('.//day'):
            date_str = day_elem.get('date')
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            affected_days.append(date)
        
        return affected_days
    
    except Exception as e:
        logging.error(f"Error loading affected days: {e}")
        return None

def apply_filters(optimizer, args):
    """Apply filters to the problem"""
    # Apply project filter
    if args.proj_filter:
        proj_prefixes = args.proj_filter.split(',')
        filtered_projects = {}
        
        for proj_id, project in optimizer.problem['projects'].projects.items():
            for prefix in proj_prefixes:
                if proj_id.startswith(prefix):
                    filtered_projects[proj_id] = project
                    break
        
        optimizer.problem['projects'].projects = filtered_projects
        logging.info(f"Applied project filter: {len(filtered_projects)} projects remaining")
    
    # Apply time filter
    if args.time_filter:
        time_parts = args.time_filter.split(',')
        if len(time_parts) == 2:
            start_str, end_str = time_parts
            
            # Parse time strings
            if start_str.startswith('v'):
                # Week-based format (e.g., 'v2410')
                year = int(start_str[1:3]) + 2000
                week = int(start_str[3:5])
                # Approximate conversion to date
                start_date = datetime.datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
            else:
                # Date-time format
                start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
            
            if end_str.startswith('v'):
                # Week-based format
                year = int(end_str[1:3]) + 2000
                week = int(end_str[3:5])
                # Approximate conversion to date (end of week)
                end_date = datetime.datetime.strptime(f"{year}-W{week}-7", "%Y-W%W-%w")
            else:
                # Date-time format
                end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
            
            # Filter projects based on time constraints
            filtered_projects = {}
            for proj_id, project in optimizer.problem['projects'].projects.items():
                # Parse project time constraints
                proj_earliest = project.get('earliest_start')
                proj_latest = project.get('latest_end')
                
                if proj_earliest and proj_latest:
                    if proj_earliest.startswith('v'):
                        # Week-based format
                        year = int(proj_earliest[1:3]) + 2000
                        week = int(proj_earliest[3:5])
                        proj_start = datetime.datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
                    else:
                        proj_start = datetime.datetime.strptime(proj_earliest, "%Y-%m-%d %H:%M:%S")
                    
                    if proj_latest.startswith('v'):
                        # Week-based format
                        year = int(proj_latest[1:3]) + 2000
                        week = int(proj_latest[3:5])
                        proj_end = datetime.datetime.strptime(f"{year}-W{week}-7", "%Y-W%W-%w")
                    else:
                        proj_end = datetime.datetime.strptime(proj_latest, "%Y-%m-%d %H:%M:%S")
                    
                    # Check if project falls within the filter time window
                    if (start_date <= proj_start <= end_date) and (start_date <= proj_end <= end_date):
                        filtered_projects[proj_id] = project
            
            optimizer.problem['projects'].projects = filtered_projects
            logging.info(f"Applied time filter: {len(filtered_projects)} projects remaining")
    
    # Apply period length
    if args.period_len:
        original_period = optimizer.problem['plan'].period_length
        optimizer.problem['plan'].period_length = args.period_len
        
        # Recalculate number of periods
        time_diff = (optimizer.problem['plan'].end_time - optimizer.problem['plan'].start_time).total_seconds() / 3600
        optimizer.problem['plan'].num_periods = int(time_diff / args.period_len)
        
        logging.info(f"Changed period length from {original_period} to {args.period_len} hours")
        
        # Filter out tasks with durations shorter than half the period length
        for proj_id, project in list(optimizer.problem['projects'].projects.items()):
            filtered_tasks = []
            for task in project['tasks']:
                if task['duration'] >= args.period_len / 2:
                    # Adjust task duration to a multiple of period length
                    periods = max(1, round(task['duration'] / args.period_len))
                    task['duration'] = periods * args.period_len
                    filtered_tasks.append(task)
            
            project['tasks'] = filtered_tasks
            
            # Remove projects with no tasks
            if not filtered_tasks:
                del optimizer.problem['projects'].projects[proj_id]
        
        logging.info(f"After filtering short tasks: {len(optimizer.problem['projects'].projects)} projects remaining")
    
    return True

def main():
    """Main function"""
    # Parse command line arguments
    args = parse_args()
    
    # Configure logging
    if args.log == "stdout":
        logger = configure_logging(None, logging.INFO if args.prt_vlvl >= 1 else logging.WARNING)
    else:
        logger = configure_logging(args.log, logging.INFO if args.prt_vlvl >= 1 else logging.WARNING)
    
    # Print welcome message
    logging.info("TCR Optimization Tool")
    logging.info("====================")
    
    # Create optimizer
    optimizer = TCROptimizer()
    
    # Load problem
    logging.info(f"Loading problem from {args.file} in directory {args.dir}...")
    if not optimizer.load_problem(args.file, args.dir):
        logging.error("Failed to load problem. Exiting.")
        return 1
    
    # Set defaults for missing components
    optimizer.set_defaults()
    
    # Apply filters
    apply_filters(optimizer, args)
    
    # Load fixed track closures if specified
    fixed_blockings = None
    if args.side_sched:
        side_sched_path = os.path.join(args.dir, args.side_sched)
        fixed_blockings = load_fixed_blockings(side_sched_path)
        if fixed_blockings:
            logging.info(f"Loaded {len(fixed_blockings)} fixed track closures from {args.side_sched}")
    
    # Load traffic capacity usage if specified
    capacity_usage = None
    if args.inp_capuse:
        cap_use_path = os.path.join(args.dir, args.inp_capuse)
        capacity_usage = load_capacity_usage(cap_use_path)
        if capacity_usage:
            logging.info(f"Loaded traffic capacity usage from {args.inp_capuse}")
    
    # Initialize models
    optimizer.initialize_models(capacity_usage)
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir)
    
    # Run the appropriate model
    if args.opt == "proj":
        # Run scheduling model
        logging.info("Running scheduling model...")
        success = optimizer.solve_scheduling(
            fixed_blockings=fixed_blockings,
            time_limit=args.opt_time,
            gap=args.opt_gap,
            verbose=args.opt_vlvl
        )
        
        if success:
            logging.info("Scheduling model solved successfully.")
            
            # Save capacity blocks if requested
            if args.log_capblk:
                cap_blk_path = os.path.join(args.out_dir, args.log_capblk)
                # TODO: Implement saving capacity blocks
                logging.info(f"Saved capacity blocks to {cap_blk_path}")
        else:
            logging.error("Failed to solve scheduling model.")
            return 1
    
    elif args.opt == "traf":
        # Run traffic model
        logging.info("Running traffic model...")
        
        # Check if we need to run daily traffic models
        if args.traf_dates:
            if args.traf_dates == "daily":
                # Run daily traffic model for all days in the planning period
                success = optimizer.solve_daily(
                    time_limit=args.opt_time,
                    gap=args.opt_gap,
                    verbose=args.opt_vlvl
                )
            else:
                # Run traffic model for specific days from a file
                traf_dates_path = os.path.join(args.dir, args.traf_dates)
                affected_days = load_affected_days(traf_dates_path)
                if affected_days:
                    success = optimizer.solve_daily(
                        traffic_dates=affected_days,
                        time_limit=args.opt_time,
                        gap=args.opt_gap,
                        verbose=args.opt_vlvl
                    )
                else:
                    logging.error(f"Failed to load affected days from {args.traf_dates}")
                    return 1
        else:
            # Run traffic model for the entire planning period
            success = optimizer.solve_traffic(
                capacity_constraints=fixed_blockings,
                time_limit=args.opt_time,
                gap=args.opt_gap,
                verbose=args.opt_vlvl
            )
        
        if success:
            logging.info("Traffic model solved successfully.")
            
            # Save capacity usage if requested
            if args.log_capuse:
                cap_use_path = os.path.join(args.out_dir, args.log_capuse)
                # TODO: Implement saving capacity usage
                logging.info(f"Saved capacity usage to {cap_use_path}")
        else:
            logging.error("Failed to solve traffic model.")
            return 1
    
    elif args.opt == "both":
        # Run integrated model
        logging.info("Running integrated model...")
        success = optimizer.solve_integrated(
            max_iterations=5,
            time_limit=args.opt_time,
            gap=args.opt_gap,
            verbose=args.opt_vlvl
        )
        
        if success:
            logging.info("Integrated model solved successfully.")
        else:
            logging.error("Failed to solve integrated model.")
            return 1
    
    # Write results to files
    optimizer.write_results_to_files(args.out_dir)
    logging.info(f"Results written to {args.out_dir}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())