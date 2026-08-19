<style>
summary {
  font-size: 1em;
  font-weight: bold;
  cursor: pointer;
}
</style>


# FAQ


## General
<details>
    <summary>Why do I have to use FMU Settings</summary>
    FMU Settings replaces parts of the tedious and error-prone process of manually editing the global configuration file by providing a simple user interface for configuring your FMU project. It connects FMU data to official databases, including validation of the data. See documentation <a href="https://equinor.github.io/fmu-settings/overview.html">here</a>.
</details>

<details>
    <summary>What is SMDA?</summary>
    <a href="https://smda.equinor.com/">SMDA</a> is Equinor's official database for subsurface master data (ex. field name, well name, stratigraphic element names etc.)
</details>

<details>
    <summary>Who can I reach out to if I don't find answers to my questions in the documentation pages?</summary>
    If you need support you can reach out to the development team in the Slack channel <a href="https://equinor.enterprise.slack.com/archives/C09MFKN4NC9">fmu-settings</a> or you can post a question in the Viva Engage group <a href="https://engage.cloud.microsoft/main/org/statoil.com/groups/eyJfdHlwZSI6Ikdyb3VwIiwiaWQiOiI3OTMyMjAxIn0">FMU Users</a>. 
</details>

<details>
    <summary>Can I use FMU Settings if my Field is not in SMDA?</summary>
    No. Your field must be in SMDA for you to be able to use FMU Settings, as FMU Settings connects to SMDA for setting project masterdata, and for mapping of stratigraphy and wells to official names.
</details>

<details>
    <summary>Can I use FMU Settings even if my asset has not yet been enrolled in Sumo?</summary>
    Yes. You can use FMU Settings even if your field/asset has not yet been enrolled in Sumo. It will add metadata to your FMU results stored on the scratch disk. However, you will not be able to use cloud based-tools like Webviz or REP if your project is not in Sumo and your data is uploaded to Sumo as part of your ERT run. 
</details>

<details>
    <summary>Can two users run FMU Settings on the same project at the same time?</summary>
    Yes. More than one user can have the application open at the same time. However, to avoid people overwriting each other’s work, only one user can make edits at a time. The project can be either editable or read-only. If the project is read-only, try Enable editing. If someone else is already editing, FMU Settings shows who currently holds the lock.
</details>

<details>
    <summary>Can I keep all settings in my global config and still use FMU Settings?</summary>
    If you have one or more of these sections in your <code>global_master_config.yml</code> file you should remove them (and the corresponding files in <code>/fmuconfig/input</code>):
    <ul>
    <li>model</li>
    <li>masterdata</li>
    <li>stratigraphy</li>
    <li>access</li> </ul>
</details>

<details>
    <summary>I have just started using FMU Settings. What do I need to change in my FMU model to be able to run everything?</summary>
    If you have one or more of these sections in your <code>global_master_config.yml</code> file you should remove them (and the corresponding files in <code>/fmuconfig/input</code>):
    <ul>
    <li>model</li>
    <li>masterdata</li>
    <li>stratigraphy</li>
    <li>access</li> </ul>
    If you don't have these sections in your <code>global_master_config.yml</code> you do not need to change anything, you're good to go!
</details>


## Initialization and Getting Started
<details>
    <summary>Why is the list of projects to open empty?</summary>
    If FMU Settings opens without a project available in the dropdown list, it is because you have not initialized the project first. Check the Getting Started page on how to initialize FMU Settings.
</details>

<details>
    <summary>Why is my project opened in read only mode?</summary>
    An FMU Settings project will always open in read-only mode, and you have to specifically enable editing to be able to edit anything. By enabling edit mode a lock file will be created for your user, preventing other users from editing the project at the same time. This lock file will expire after a given time period and you will be asked if you want to keep working or release the lock file. This is similar to what you are used to with RMS and RMS lock files. 
</details>


## RMS project
<details>
    <summary>What does it mean to access the RMS project from within FMU Settings?</summary>
    To be able to edit the stratigraphy and the wellbores sections in FMU Settings you must establish the connection between FMU Settings and RMS, making RMS accessible for FMU Settings to read from. Due to a limited number of RMS licenses and license limitations, RMS is not opened by default when FMU Settings is opened. When you access the RMS project you will have an open connection to RMS for 2 hours, before the RMS connection will be automatically closed.
</details>


## Masterdata
<details>
    <summary>Why can't I see my field when I search for it?</summary>
    If your field is not available in the list it means that your field is not in SMDA. To be able to map your project to official masterdata your field must exist in SMDA. See <a href="https://equinor.github.io/fmu-settings/overview.html">here</a>.
</details>

<details>
    <summary>Can I add a stratigraphic column from a neighboring field when my field does not have its own stratigraphic column?</summary>
    No. Adding a stratigraphic column from a neighboring field is not possible. To be able to add a stratigraphic column your field must have at least one stratigraphic column in SMDA.
</details>


## Mapping
<details>
    <summary>I have updated my stratigraphic framework in RMS. What do I need to do in FMU Settings to include the updated stratigraphy in my project?</summary>
    If you have made changes to the stratigraphic column in RMS you must open FMU Settings for your project, access the RMS project, and then add and/or remove horizons and zones accordingly. If you have added horizons and/or zones these must also be mapped, see the stratigraphy mapping page.
</details>

<details>
    <summary>I have added new wells to RMS. What do I need to do in FMU Settings to add the new wells to my project?</summary>
    If you have made changes to the wells in RMS you must open FMU Settings for your project, access the RMS project, and then add and/or remove wells accordingly. If you have added one or more wells, these must also be mapped, see the wellbore mapping page.
</details>

<details>
    <summary>Do I have to map my RMS wells to Simulator wells to be able to visualize my wells in Webviz?</summary>
    No. Mapping wellbores between RMS and Simulator is optional. If you want to upload RMS wells to SUMO (for instance to be able to visualize them in Webviz), the only mandatory step is to map the RMS well names to SMDA well names.
</details>


## Synchronization between projects
<details>
    <summary>I have made changes to FMU Settings in my user copy. How can I merge these changes into the Master project?</summary>
    To copy FMU Settings from one revision to another, you can use the terminal command <code>fmu sync</code>. See the documentation for instructions on how to use this command <a href="https://equinor.github.io/fmu-settings/terminal_commands.html">here</a>.
</details>

<details>
    <summary>I merged FMU Settings from my user revision to the master revision by accident. What should I do to roll back to a previous version?</summary>
    If you have saved changes in FMU Settings, you will have previous versions stored as snapshots on the History page. Here you can pick a previous version (snapshot) and restore it. The current version will then be overwritten by the snapshot version you have chosen.
</details>


## Access and Authentication
<details>
    <summary>Why do I have to log on and authenticate every time I want to make changes to my project's masterdata?</summary>
    You have to log on and authenticate to be able to access data in SMDA. 
</details>


## Troubleshooting
<details>
    <summary>I have edited something in my .fmu folder manually. Is there a way to get back a previous version?</summary>
    No, which also is also why users should never edit the content of .fmu manually.
</details>

<details>
    <summary>When I open FMU Settings it seems to be an empty project and it shows an error message saying "Network error". What is wrong?</summary>
    If you get an empty project and a network error when opening FMU Settings, try performing a hard refresh of your browser (Ctrl + Shift + R)
</details>
