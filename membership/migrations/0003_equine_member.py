# Generated by Django 3.1.2 on 2020-11-09 20:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0002_auto_20201108_1602'),
    ]

    operations = [
        migrations.AddField(
            model_name='equine',
            name='member',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='emember', to='membership.member', verbose_name='Equine Member'),
        ),
    ]
