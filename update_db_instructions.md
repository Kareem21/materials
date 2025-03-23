# Installing the Budget Control Module

After copying the module files, follow these steps to properly install the module:

## Step 1: Update the Module List
1. Log in to Odoo with administrator privileges
2. Go to **Apps** menu
3. Click on **Update Apps List** in the top menu

## Step 2: Install the Module
1. Search for "Material Budget" in the apps list
2. Click **Install** button on the Material Budget module

## Step 3: Verify Installation
After installation, you should see:
1. A new "Material Budget" menu in the main menu
2. Cost Sheets, Material Requests, and Purchase Orders submenus

## If You See Errors During Installation
If you encounter database column errors (like "column X does not exist"), use one of these methods:

### Option 1: Through the Odoo Web Interface
1. Go to **Apps** menu
2. Find and click on the **Materials** module in the list
3. Click the **Upgrade** button
4. After upgrade completes, refresh your browser

### Option 2: Through Command Line
Run the following command in your Odoo instance:

```bash
python3 -m odoo -c /path/to/your/odoo.conf -d your_database_name -u materials
```

Replace `/path/to/your/odoo.conf` with the path to your Odoo configuration file and `your_database_name` with the name of your database.

## Using the Budget Control Features
1. First, create Cost Sheets for your projects with budget lines
2. When creating Material Requests or Purchase Orders, select the project
3. The system will automatically find matching cost sheet lines
4. If budget is exceeded, you'll see warnings in red
