# Generated by Django 2.2 on 2019-05-15 22:11

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('PuzzModel', '0008_auto_20190515_2153'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nickname', models.CharField(max_length=20)),
                ('email', models.CharField(max_length=150)),
                ('sof', models.BooleanField()),
                ('storyid', models.IntegerField(blank=True, null=True)),
                ('fragid', models.IntegerField(blank=True, null=True)),
                ('content', models.CharField(max_length=150)),
                ('createtime', models.DateTimeField(default=django.utils.timezone.now)),
                ('likescount', models.IntegerField(default=0)),
            ],
        ),
        migrations.DeleteModel(
            name='Commenttable',
        ),
    ]