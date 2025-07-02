import subprocess
import os
import logging
import json
import yaml
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)

# Define a path for robot workspaces - this can be configured in settings.py
ROBOT_WORKSPACE_PATH = getattr(settings, 'ROBOT_WORKSPACE_PATH', 
                               os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                               'robot_workspaces'))

def ensure_robot_workspace_exists():
    """Ensure the robot workspace directory exists"""
    os.makedirs(ROBOT_WORKSPACE_PATH, exist_ok=True)
    return ROBOT_WORKSPACE_PATH

def get_robot_path(robot_id: str) -> str:
    """
    Get the path to a specific robot workspace
    
    Args:
        robot_id (str): The ID of the robot
        
    Returns:
        str: Full path to the robot workspace
    """
    workspace_path = ensure_robot_workspace_exists()
    return os.path.join(workspace_path, f"robot-{robot_id}")

def run_rcc_command(command: List[str], cwd: Optional[str] = None, env: Optional[Dict] = None) -> Tuple[int, str, str]:
    """
    Run an RCC command and return the result
    
    Args:
        command (List[str]): RCC command to run
        cwd (Optional[str]): Working directory for the command
        env (Optional[Dict]): Additional environment variables
        
    Returns:
        Tuple[int, str, str]: Return code, stdout, and stderr
    """
    try:
        logger.info(f"Running RCC command: {' '.join(command)}")
        
        # Prepare environment
        cmd_env = os.environ.copy()
        if env:
            cmd_env.update(env)
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=cmd_env
        )
        
        stdout, stderr = process.communicate()
        return_code = process.returncode
        
        if return_code != 0:
            logger.error(f"RCC command failed with return code {return_code}: {stderr}")
        
        return return_code, stdout, stderr
    
    except Exception as e:
        logger.exception(f"Error running RCC command: {e}")
        return 1, "", str(e)

def initialize_robot_workspace(robot_id: str, robot_dir_path: str) -> bool:
    """
    Initialize a robot workspace from a directory containing robot.yaml
    
    Args:
        robot_id (str): The ID of the robot
        robot_dir_path (str): Path to directory containing robot.yaml
        
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    robot_workspace = get_robot_path(robot_id)
    
    # Create robot workspace directory if it doesn't exist
    if not os.path.exists(robot_workspace):
        os.makedirs(robot_workspace, exist_ok=True)
    else:
        # Clean the directory if it exists
        logger.info(f"Cleaning existing robot workspace at {robot_workspace}")
        for item in os.listdir(robot_workspace):
            item_path = os.path.join(robot_workspace, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
    
    # Check if source directory exists and has robot.yaml
    robot_yaml_path = os.path.join(robot_dir_path, "robot.yaml")
    if not os.path.exists(robot_yaml_path):
        logger.error(f"Robot definition not found at {robot_yaml_path}")
        return False
    
    # Copy all files from source directory to robot workspace
    try:
        # Use shutil to copy files recursively
        for item in os.listdir(robot_dir_path):
            s = os.path.join(robot_dir_path, item)
            d = os.path.join(robot_workspace, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        logger.info(f"Copied robot files to {robot_workspace}")
    except Exception as e:
        logger.error(f"Failed to copy robot files: {e}")
        return False
    
    # No need for specific RCC initialization - RCC will handle this during first run
    # The correct workflow is to just copy the robot files and let RCC manage the environment
    
    return True

def run_robot(robot_id: str, task_name: Optional[str] = None, env_vars: Optional[Dict[str, str]] = None) -> Dict:
    """
    Run a robot using RCC
    
    Args:
        robot_id (str): The ID of the robot
        task_name (Optional[str]): Name of the task to run, if not specified uses the first task
        env_vars (Optional[Dict[str, str]]): Environment variables for the robot run
        
    Returns:
        Dict: Results of the robot run
    """
    robot_dir = get_robot_path(robot_id)
    robot_yaml_path = os.path.join(robot_dir, "robot.yaml")
    
    if not os.path.exists(robot_dir) or not os.path.exists(robot_yaml_path):
        return {
            "success": False,
            "error": f"Robot workspace for {robot_id} does not exist or is missing robot.yaml"
        }
    
    # If no task specified, find the first available task
    if not task_name:
        tasks = get_robot_tasks(robot_id)
        if not tasks:
            return {
                "success": False,
                "error": "No tasks available in robot.yaml"
            }
        task_name = tasks[0]
    
    # Create environment variables JSON file for the robot if needed
    env_file = None
    if env_vars:
        # Make sure the devdata directory exists
        devdata_dir = os.path.join(robot_dir, "devdata")
        os.makedirs(devdata_dir, exist_ok=True)
        
        # Create the env.json file
        env_file = os.path.join(devdata_dir, "env.json")
        with open(env_file, "w") as f:
            json.dump(env_vars, f)
            logger.info(f"Created environment file at {env_file}")
    
    # Run the robot with the specified task using the correct RCC command
    cmd = [
        "rcc", 
        "run",
        "--robot", robot_yaml_path,
        "--task", task_name
    ]
    
    if env_file:
        cmd.extend(["--environment", env_file])
    
    # Run the robot
    return_code, stdout, stderr = run_rcc_command(cmd, cwd=robot_dir)
    
    result = {
        "success": return_code == 0,
        "stdout": stdout,
        "stderr": stderr,
        "return_code": return_code,
        "task_name": task_name
    }
    
    # Try to parse output artifacts if successful
    output_dir = os.path.join(robot_dir, "output")
    if os.path.exists(output_dir):
        result["output_dir"] = output_dir
        
        # Look for output.json, artifacts, or work items
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            if item.endswith('.json') and os.path.isfile(item_path):
                try:
                    with open(item_path, "r") as f:
                        result[item] = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load artifact {item}: {e}")
    
    return result

def get_robot_tasks(robot_id: str) -> List[str]:
    """
    Get available tasks in a robot by reading the robot.yaml file
    
    Args:
        robot_id (str): The ID of the robot
        
    Returns:
        List[str]: List of available task names
    """
    robot_dir = get_robot_path(robot_id)
    robot_yaml_path = os.path.join(robot_dir, "robot.yaml")
    
    if not os.path.exists(robot_yaml_path):
        logger.error(f"No robot.yaml found at {robot_yaml_path}")
        return []
    
    try:
        with open(robot_yaml_path, 'r') as f:
            robot_config = yaml.safe_load(f)
        
        tasks = robot_config.get('tasks', {})
        return list(tasks.keys())
    
    except Exception as e:
        logger.error(f"Failed to parse robot.yaml file: {e}")
        return []
