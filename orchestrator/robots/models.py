from django.db import models
from django.contrib.auth.models import User
from utils.choices import Platform, StatusRobot
# Create your models here.


class Robot(models.Model):
    user_id = models.OneToOneField(User, null=False, blank=False,
                                   on_delete=models.CASCADE)
    ip_address = models.CharField(null=False, blank=False,
                                  unique=True, max_length=15)
    platform = models.CharField(null=False, blank=False, max_length=50,
                                choices=Platform.choices,
                                default=Platform.OTHER)
    status = models.CharField(null=False, blank=False, max_length=50,
                              choices=StatusRobot.choices,
                              default=StatusRobot.INACTIVE)
    robot_yaml_path = models.CharField(max_length=255, null=True, blank=True,
                                       help_text="Path to the robot.yaml file")
    initialized = models.BooleanField(default=False, 
                                      help_text="Whether the robot workspace has been initialized")
    available_tasks = models.JSONField(null=True, blank=True,
                                       help_text="Available tasks in this robot")

    def __str__(self) -> str:
        return self.ip_address
