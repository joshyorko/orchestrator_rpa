from django.apps import AppConfig



class RobotsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'robots'

    def ready(self):
        from django.db.models.signals import post_migrate
        from django.dispatch import receiver
        from robots import tasks as robot_tasks

        def create_periodic_tasks(sender, **kwargs):
            from django_celery_beat.models import PeriodicTask, IntervalSchedule
            # Create or get an interval schedule to run the task every 3 minutes
            schedule_handle, _ = IntervalSchedule.objects.get_or_create(
                every=3,
                period=IntervalSchedule.MINUTES,
            )
            try:
                robot_tasks.periodic_task_handle = PeriodicTask.objects.get(
                    name='handle_disconnected_robots')
            except PeriodicTask.DoesNotExist:
                robot_tasks.periodic_task_handle = PeriodicTask.objects.create(
                    interval=schedule_handle,
                    name='handle_disconnected_robots',
                    task='robots.tasks.handle_disconnected_robots',
                    enabled=True,
                )

            # Create or get an interval schedule to run the task every 1 minute
            schedule_check, _ = IntervalSchedule.objects.get_or_create(
                every=1,
                period=IntervalSchedule.MINUTES,
            )
            try:
                robot_tasks.periodic_task_check = PeriodicTask.objects.get(
                    name='check_robots_every_minute')
            except PeriodicTask.DoesNotExist:
                robot_tasks.periodic_task_check = PeriodicTask.objects.create(
                    interval=schedule_check,
                    name='check_robots_every_minute',
                    task='robots.tasks.check_robots_every_minute',
                    enabled=False,
                )

        post_migrate.connect(create_periodic_tasks, sender=self)
