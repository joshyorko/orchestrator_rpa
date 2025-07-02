from django_celery_beat.models import PeriodicTask, IntervalSchedule
from tasks.utils import get_tasks_from_items
from items.utils import get_items
from robots.utils import (check_disconnected_robots, change_status_inactive,
                          assing_robots, get_min_robot, get_active_robots,
                          remove_robots)
from orchestrator.celery import app
from orchestrator.memory_manager import get_memory
from robots.robocorp_utils.rcc_runner import (
    initialize_robot_workspace, 
    run_robot, 
    get_robot_tasks
)
import logging

logger = logging.getLogger(__name__)


periodic_task_handle = None



@app.task
def handle_disconnected_robots():
    """
    Celery task to handle disconnected robots.

    This task is scheduled to run periodically and performs
    the following actions:
    1. Searches for disconnected robots.
    2. Changes the state of disconnected robots to inactive.
    3. Retrieves items associated with disconnected robots and their
       corresponding tasks.
    4. Removes robot assignments from items and tasks.
    5. Checks if there are active robots. If there are no active robots,
       enables the periodic task for robot verification.

    Returns:
    None
    """
    robots_disconnecteds = check_disconnected_robots()

    if robots_disconnecteds:
        change_status_inactive(robots_disconnecteds)
        items = get_items(robots_disconnecteds).all()
        if items:
            tasks = get_tasks_from_items(items)
            remove_robots([items, tasks])
            items = items.none()
            tasks = tasks.none()
    robots_active = get_active_robots()
    if not robots_active:
        periodic_task_check.enabled = True
        periodic_task_check.save()


periodic_task_check = None


@app.task
def check_robots_every_minute():
    """
    Celery task to check robots every minute.

    This task is scheduled to run periodically and performs the following
    actions:
    1. If the task to handle disconnected robots is enabled, it disables
       it and logs a message.
    2. Searches for active robots.
    3. If there are active robots, it checks if the memory has unassigned
       items.
    4. If the memory has unassigned items, it assigns the items and tasks
       to a robot and clears the memory.
    5. Disables the task to check active robots and enables the task to handle
       disconnected robots.
    6. If there are no active robots, enables the task to check disconnected
       robots.

    Returns:
    None
    """
    if periodic_task_handle.enabled:
        periodic_task_handle.enabled = False
        periodic_task_handle.save()
    memory = get_memory()
    robots = get_active_robots()
    if robots:
        if not memory.items.exists():
            memory.items = get_items(robots=None).all()
            if memory.items.exists():
                robot = get_min_robot()
                memory.task = get_tasks_from_items(memory.items).all()
                assing_robots(memory.items, robot)
                assing_robots(memory.task, robot)
                memory.clear()
            periodic_task_check.enabled = False
            periodic_task_handle.enabled = True
            periodic_task_handle.save()
            periodic_task_check.enabled = False
            periodic_task_check.save()


# ROBOCORP RCC INTEGRATION TASKS

@app.task
def initialize_robot_workspace_task(robot_id, robot_yaml_path):
    """
    Initialize a robot workspace for RCC
    
    Args:
        robot_id: ID of the robot
        robot_yaml_path: Path to the robot.yaml file
        
    Returns:
        bool: Success status
    """
    logger.info(f"Initializing robot workspace for robot_id={robot_id}, path={robot_yaml_path}")
    success = initialize_robot_workspace(robot_id, robot_yaml_path)
    
    if success:
        from robots.models import Robot
        robot = Robot.objects.get(id=robot_id)
        
        # Get available tasks
        available_tasks = get_robot_tasks(robot_id)
        robot.available_tasks = available_tasks
        robot.initialized = True
        robot.save()
        
        logger.info(f"Robot workspace initialized successfully for robot_id={robot_id}")
        logger.info(f"Available tasks: {available_tasks}")
    else:
        logger.error(f"Failed to initialize robot workspace for robot_id={robot_id}")
    
    return success

@app.task
def run_robot_task(robot_id, task_name=None, env_vars=None, task_id=None, item_id=None):
    """
    Run a robot task using RCC
    
    Args:
        robot_id: ID of the robot
        task_name: Name of the task to run
        env_vars: Environment variables
        task_id: Optional Django task ID for updating status
        item_id: Optional item ID for updating status
        
    Returns:
        dict: Result of robot run
    """
    from robots.models import Robot
    
    try:
        robot = Robot.objects.get(id=robot_id)
    except Robot.DoesNotExist:
        logger.error(f"Robot with id {robot_id} does not exist")
        return {"success": False, "error": f"Robot {robot_id} not found"}
    
    if not robot.initialized:
        logger.error(f"Robot {robot_id} is not initialized")
        return {"success": False, "error": f"Robot {robot_id} not initialized"}
    
    # Prepare environment variables
    if env_vars is None:
        env_vars = {}
    
    # Add task_id and item_id if provided
    if task_id:
        env_vars["TASK_ID"] = str(task_id)
    if item_id:
        env_vars["ITEM_ID"] = str(item_id)
    
    # Add API endpoint for callbacks
    # env_vars["API_ENDPOINT"] = settings.API_URL
    
    logger.info(f"Running robot task: robot_id={robot_id}, task_name={task_name}")
    result = run_robot(robot_id, task_name, env_vars)
    
    if result.get("success"):
        logger.info(f"Robot task completed successfully: robot_id={robot_id}, task_name={task_name}")
    else:
        logger.error(f"Robot task failed: robot_id={robot_id}, task_name={task_name}")
        logger.error(f"Error: {result.get('stderr')}")
    
    return result
