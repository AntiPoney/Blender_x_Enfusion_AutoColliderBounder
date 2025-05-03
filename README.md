# Blender X Enfusion - Auto Collider Bounder

A Blender add-on for creating / converting mesh objects into clicks ready colliders for Enfusion Engine

## Features

- Create an automatic and self bounding collider(s) from the current selected object(s)
  - Box collider
  - Sphere collider
  - Capsule collider
  - Cylinder collider
  - Convex collider (from complex mesh)

- Convert any object(s) mesh(es) into a click ready collider(s) :
  - Convex collider
  - triangle collider

## Installation

1. Download the zip file from the latest release 
2. Open Blender
3. Go to `Edit` > `Preferences` > `Add-ons` > `drop-down arrow`
4. Click `Install...` and select the ZIP file you downloaded
5. Enable the addon by checking the box

## location 

`3D viewport` > `right side` > `Enfusion Tools` > `colliders tools`

## Usage

1. Select one or more objects in the 3D Viewport
2. press `Create Collider` if you wish to create a new object for the collider
3. for complex collision, I encoure you to create the object yourself,
    when you are ready to bake it, press `Convert To Collider`
4. Follow the dialog box, in case of doubt, hover the buttons to get a hint information
5. you're ready to export !


## Notes

- The add-on creates a new object as the collider and does not modify the original mesh (except for converting)
- Convex and triangles colliders are based on the original mesh's geometry, so it is CRUCIAL to simplify the mesh beforehand

## License

MIT License
