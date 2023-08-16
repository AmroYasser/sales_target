# Sales Target

Sales Target is an Odoo module that deals with companies' sales targets.

## Technologies
Odoo 12 \
xlrd 1.2.0

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install the requirement

```bash
pip install -r requirements.txt
```
Then run Odoo 12, as usual, and install the module.

## Usage
### The following criteria should be met or an error will be raised:
- Total targets of point-of-sales shops must equal the company target (unless the state is set to draft).
- Total target for employees at each point of sales shop must equal the shop's target.
- POS shops must be unique per company.
- Employees must be unique per all shops.
- The company should not have more than one target in the same period.

### Generate the data from excel file:
Upload the excel file that matches the template (see the template in 'template' directory).
![upload file](https://github.com/AmroYasser/sales_target/blob/main/imgs/upload_file.png?raw=true)

After uploading the file, press generate to see the form view filled with the data.
![upload file](https://github.com/AmroYasser/sales_target/blob/main/imgs/generate.png?raw=true)




## To do
Add a report to compare the company sales targets with the actual sales.
