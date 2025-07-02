# Robocorp Integration with Orchestrator RPA

## Overview

This document describes how Robocorp RCC (Robot Control Center) has been integrated with the Orchestrator RPA system. This integration allows the orchestrator to execute and manage Robocorp robots.

## Directory Structure

- `/robot_workspaces/`: Root directory for all robot workspaces
  - `/robot_workspaces/robot-{id}/`: Workspace for each robot, where `{id}` is the robot ID

## Integration Components

1. **RCC Runner Utility**: `orchestrator/robots/robocorp_utils/rcc_runner.py`
   - Core functionality for running and managing robots

2. **Robot Model Extensions**: Added fields to the Robot model to track the robot.yaml path and available tasks

3. **Celery Tasks**: Tasks for initializing robot workspaces and running robots

## RCC Commands

The primary RCC commands used:

1. **Run Robot Task**:
   ```bash
   rcc run --robot /path/to/robot.yaml --task TaskName
   ```

2. **Environment Variables**:
   Environment variables can be passed to robots by creating a `devdata/env.json` file and passing it with:
   ```bash
   rcc run --robot /path/to/robot.yaml --task TaskName --environment /path/to/env.json
   ```

## Integration Flow

1. **Robot Registration**:
   - Robot is registered in the system with the path to the robot.yaml file
   - Robot workspace is initialized by copying files to the robot workspace directory

2. **Robot Initialization**:
   - The robot files are copied to the robot workspace
   - Available tasks are extracted from robot.yaml

3. **Task Execution**:
   - When a task is assigned to a robot, a Celery task is created
   - RCC is used to run the robot task
   - Results and artifacts are collected

## Development Notes

- **Testing**: To test the integration, you can use the `test-robocorp-bot` folder as an example robot.

- **Environment Setup**: Make sure the Docker container has RCC installed and available in the PATH.

- **Work Items**: Robocorp work items can be managed by creating appropriate JSON files in the robot workspace.

## Running the System

1. Build and run the Docker containers:
   ```bash
   docker-compose up -d
   ```

2. Initialize a robot in the Django admin or API by providing the path to the robot.yaml file

3. Assign tasks to the robot through the Orchestrator UI or API

## Troubleshooting

- If robot execution fails, check the logs in the robot's output directory
- Make sure RCC is installed correctly in the Docker container
- Verify that the robot.yaml file has valid task definitions
