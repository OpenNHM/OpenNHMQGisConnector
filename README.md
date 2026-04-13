# OpenNHMQGisConnector
The QGis to OpenNHM Connector, providing the necessary files to be loaded in
QGis. See https://docs.avaframe.org/en/latest/ for more information regarding
installation and usage.

### License 
Licensed with [![European Public License EUPL](https://img.shields.io/badge/license-EUPL-green.png)](https://github.com/OpenNHM/OpenNHMQGisConnector/blob/master/LICENSE)


### For development: 

To run qgis, you can use the provided pixi environment:
`pixi run --environment qgis qgis`

for the pb_tool
`pixi run pb_tool deploy`

Local deployment is possible via
- `pb_tool deploy`
This will copy the current version to your local QGis directory -> see `pb_tool.cfg`

### To deploy

- change version info in `metadata.txt`

- clean __pycache__:
 `find . -type d -name __pycache__ -exec rm -rf {} +`

- use `pb_tool zip` to generate uploadable zip

- Upload to https://plugins.qgis.org
