# Odoo 18 Code Syntax Changes

Odoo 18 has introduced a plethora of new features and improvements, not just in functionality but also in its code structure and syntax. For developers, understanding these changes is essential to seamlessly transition from older versions like Odoo 16. This article highlights the critical updates to Odoo 18’s code syntax and provides guidance on adapting your modules.

## 1. XML Tag Changes: From `tree` to `list`
One of the most prominent changes in Odoo 18 is the renaming of the `tree` tag to `list`. This change is straightforward but affects all views that previously utilized the `tree` tag.

**Before:**
```xml
<tree>
    <field name="name"/>
</tree>
```
**After:**
```xml
<list>
    <field name="name"/>
</list>
```
This change enhances consistency and clarity in XML syntax.

## 2. `attrs` and `states` Attribute Simplifications
Odoo 18 simplifies the use of conditional attributes by replacing `attrs` and `states` with direct attributes.

### a. One condition
**Before:**
```xml
<field name="shift_id" attrs="{'invisible': [('shift_schedule', '=', [])]}"/>
```
**After:**
```xml
<field name="shift_id" invisible="not shift_schedule"/>
```

### b. Two conditions (with OR)
**Before:**
```xml
<field name="department_id" attrs="{'invisible': ['|', ('state', '=', 'done'), ('type', '=', 'internal')]}"/>
```
**After:**
```xml
<field name="department_id" invisible="state == 'done' or type == 'internal'"/>
```

### c. Two conditions (with AND)
**Before:**
```xml
<field name="job_position" attrs="{'readonly': [('state', '=', 'approved'), ('user_id', '!=', user.id)]}"/>
```
**After:**
```xml
<field name="job_position" readonly="state == 'approved' and user_id != user.id"/>
```

Similarly, the `states` attribute is replaced by conditions like:

**Before:**
```xml
<button string="Submit" states="draft"/>
```
**After:**
```xml
<button string="Submit" invisible="state != 'draft'"/>
```
These changes make the XML cleaner and easier to maintain.

## 3. Widget Updates: The `daterange` Widget
The `daterange` widget has been updated for better functionality.

**Before:**
```xml
<div>
    <field name="start_date" widget="daterange" options="{'related_end_date': 'end_date'}"/>
    <field name="end_date" widget="daterange" options="{'related_start_date': 'start_date'}"/>
</div>
```
**After:**
```xml
<div>
    <field name="start_date" widget="daterange" options="{'end_date_field': 'end_date'}"/>
</div>
```
This reduces redundancy and simplifies the options configuration.

## 4. Chatter Simplification
Odoo 18 introduces a new way to define the chatter, eliminating the need for verbose XML.

**Before:**
```xml
<div class="oe_chatter">
    <field name="message_follower_ids" widget="mail_followers"/>
    <field name="activity_ids" widget="mail_activity"/>
    <field name="message_ids" widget="mail_thread"/>
</div>
```
**After:**
```xml
<chatter/>
```
For additional customization, you can use:
```xml
<chatter reload_on_follower="True"/>
```

## 5. Removal of `Not Number Call` and `Doall` in Scheduled Actions
Odoo 18 has deprecated the use of `Not Number Call` and `Doall` in scheduled actions (cron jobs). Ensure your custom actions align with these updates by refactoring your code.

## 6. `states` in Field Models Removed
Odoo 18 has removed the `states` attribute in Python field definitions. Instead, the logic should be handled directly in the UI or through other means.

**Before:**
```python
date = fields.Date(
    string='Date',
    index=True,
    compute='_compute_date', store=True, required=True, readonly=False, precompute=True,
    states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]},
    copy=False,
    tracking=True,
)
```
**After:**
```python
date = fields.Date(
    string='Date',
    index=True,
    compute='_compute_date', store=True, required=True, readonly=False, precompute=True,
    copy=False,
    tracking=True,
)
```

## 7. Structural Changes in `res.config` XML
The structure of `res.config.settings` has been simplified in XML. Settings are now grouped into blocks with `app` and `block` tags.

**Before:**
```xml
<record id="res_config_settings_view_inherit_example" model="ir.ui.view">
    <field name="name">res.config.settings.view.form.inherit.example</field>
    <field name="model">res.config.settings</field>
    <field name="inherit_id" ref="base.res_config_settings_view_form"/>
    <field name="arch" type="xml">
        <xpath expr="//form" position="inside">
           <div class="app_settings_block" data-string="application_settings" string="Application Settings" data-key="key_example">
              <h2>Example Settings</h2>
              <field name="example_setting"/>
           </div>
        </xpath>
    </field>
</record>
```
**After:**
```xml
<record model="ir.ui.view" id="res_config_settings_view">
    <field name="arch" type="xml">
        <xpath expr="//form" position="inside">
            <app string="Application Settings">
                <block title="Example Settings">
                    <setting string="Example Setting" help="Description for the example setting">
                        <field name="example_setting"/>
                    </setting>
                </block>
            </app>
        </xpath>
    </field>
</record>
```
### Explanation:
- From `<div class="app_settings_block">` to `<app>`: `app_settings_block` is replaced with `app` to group settings logically.
- From `<h2>` to `<block>` titles: Headers defined using `<h2>` are now incorporated directly as block titles.
- From nested `div` containers to `setting` tags: Fields and their descriptions are encapsulated within `setting` tags, streamlining the layout.
- Addition of `help` attributes: Inline descriptions are now provided using the `help` attribute within `setting` tags.

## Conclusion
Migrating to Odoo 18 involves adapting to these syntactic changes to ensure compatibility and leverage the new features. These updates not only improve code readability but also align with modern development practices.

Stay tuned for more insights into Odoo development, and don’t forget to explore the official documentation for a deeper dive into Odoo 18.


&amp;&amp; instead of && for xml? 



  1. Database Structure:
    - There are two main models involved:
        - hr.timesheet.entry: Stores the header information (employee, supervisor, date range, status)
      - hr.timesheet.line: Stores the individual day entries (date, hours, project, etc.)
  2. How Lines Are Stored:
    - All timesheet lines are stored in the hr.timesheet.line table
    - Each line is linked to a parent entry via the entry_id field
    - A line can belong to either a daily entry or a monthly entry
  3. When Daily Entries Are Submitted:
    - The system finds or creates a monthly entry for that employee and month
    - The lines from the daily entry are copied to the monthly entry
    - The original daily entry remains in the system but doesn't create duplicate records in the list view
    - This allows you to still view the daily entries when browsing by day
  4. Sharing of Values:
    - The values are not directly shared between daily and monthly entries
    - Instead, they are copied from the daily entry to the monthly entry at submission time
    - This means if you edit a daily entry after submission, you need to submit it again for the changes to appear in the monthly view
  5. Visibility in the Frontend:
    - When viewing a day in the daily entry screen, you'll see the lines you created for that day
    - When viewing a month in the monthly view, you'll see all lines for the entire month, including those added via daily entries

  This approach provides flexibility while maintaining data integrity, since all entries ultimately get consolidated into monthly entries for reporting and approval
  purposes.

