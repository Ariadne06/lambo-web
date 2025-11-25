from django.db import models

# Create your models here.
class Announcement(models.Model):
    AUDIENCE_RESIDENT = "resident"
    AUDIENCE_PERSONNEL = "personnel"
    AUDIENCE_BOTH = "both"

    AUDIENCE_CHOICES = [
        (AUDIENCE_RESIDENT, "Resident"),
        (AUDIENCE_PERSONNEL, "Personnel"),
        (AUDIENCE_BOTH, "Both"),
    ]

    announcement_id = models.AutoField(primary_key=True)
    header_title = models.CharField(max_length=255)
    details = models.TextField()
    announcement_image_path = models.CharField(
        max_length=512,
        blank=True,
        null=True,
        help_text="Relative or absolute path to the announcement image in storage",
    )
    # This is the 'date' column used in your SQL functions
    date = models.DateField()

    audience = models.CharField(
        max_length=10,
        choices=AUDIENCE_CHOICES,
        help_text="Target audience: resident, personnel, or both",
    )

    # 🔧 IMPORTANT CHANGE:
    # Just keep the raw creator ID; don't use a ForeignKey right now.
    created_by = models.IntegerField(
        db_column="created_by",
        null=True,
        blank=True,
        help_text="ID of the personnel who created this announcement",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "Announcement"
        # 🔧 Since the table is created/managed by your SQL scripts,
        # tell Django not to try to create/alter it with migrations.
        managed = False
        ordering = ["-date", "-announcement_id"]

    def __str__(self):
        return f"{self.header_title} ({self.date})"