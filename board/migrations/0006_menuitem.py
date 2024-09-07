# Generated by Django 5.0.3 on 2024-03-31 12:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('board', '0005_alter_category_parent'),
    ]

    operations = [
        migrations.CreateModel(
            name='MenuItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('rzd', 'Раздел'), ('link', 'Ссылка')])),
                ('name', models.CharField(max_length=250)),
                ('url', models.CharField(max_length=250)),
                ('add_class', models.CharField(blank=True, choices=[('abra_kadabra1', ' '), ('abra_kadabra2', ' '), ('abra_kadabra3', ' ')], null=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children_menu_item', to='board.menuitem')),
            ],
            options={
                'verbose_name': 'Пункт меню',
                'verbose_name_plural': 'Пункты меню',
            },
        ),
    ]
