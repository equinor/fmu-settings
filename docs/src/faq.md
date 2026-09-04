# FAQ
The FAQ (Frequently Asked Questions) page is designed to help you quickly find answers to common questions and issues related to FMU Settings. Before reaching out for support, we recommend checking this page to see if your question has already been answered.

The FAQ is regularly updated based on user feedback and new features, so check back often for the latest updates. 

**Still need help?** If you can’t find the answer you’re looking for, or if you have suggestions for changes and/or additions, you can reach out to the development team (Atlas team) in the Slack channel <a href="https://equinor.enterprise.slack.com/archives/C09MFKN4NC9" target="_blank" rel="noopener noreferrer">fmu-settings</a> or you can post a question in the Viva Engage group <a href="https://engage.cloud.microsoft/main/org/statoil.com/groups/eyJfdHlwZSI6Ikdyb3VwIiwiaWQiOiI3OTMyMjAxIn0" target="_blank" rel="noopener noreferrer">FMU Users</a>. 


## General
<details>
    <summary>Why do I have to use FMU Settings?</summary>
    FMU Settings replaces parts of the tedious and error-prone process of manually editing the global configuration file by providing a simple user interface for configuring your FMU project. It connects FMU data to official databases, including validation of the data. See the <a href="overview.html">Overview</a> page.
</details>

<details>
    <summary>What is SMDA?</summary>
    <a href="https://smda.equinor.com/" target="_blank" rel="noopener noreferrer">SMDA</a> is Equinor's official database for subsurface master data (e.g. field name, well name, stratigraphic element names, etc.)
</details>

<details>
    <summary>Who can I contact if I don't find answers to my questions in the documentation pages?</summary>
    If you need support you can reach out to the development team in the Slack channel <a href="https://equinor.enterprise.slack.com/archives/C09MFKN4NC9" target="_blank" rel="noopener noreferrer">fmu-settings</a> or you can post a question in the Viva Engage group <a href="https://engage.cloud.microsoft/main/org/statoil.com/groups/eyJfdHlwZSI6Ikdyb3VwIiwiaWQiOiI3OTMyMjAxIn0" target="_blank" rel="noopener noreferrer">FMU Users</a>. 
</details>

<details>
    <summary>Can I use FMU Settings if my field is not in SMDA?</summary>
    No. Your field must be in SMDA for you to be able to use FMU Settings, as FMU Settings connects to SMDA to set project master data and map stratigraphy and wells to official names. See the Sumo <a href="https://fmu-docs.equinor.com/docs/sumo/getting_started" target="_blank" rel="noopener noreferrer">Getting started</a> for information about SMDA and how to add a new field to SMDA.
</details>

<details>
    <summary>Can I use FMU Settings even if my asset has not yet been enrolled in Sumo?</summary>
    Yes. You can use FMU Settings even if your field/asset has not yet been enrolled in Sumo. It will add metadata to your FMU results stored on the scratch disk. However, you will not be able to use cloud-based tools like Webviz or REP if your project is not in Sumo and your data is not uploaded to Sumo as part of your ERT run. 
</details>

<details>
    <summary>Can two users run FMU Settings on the same project at the same time?</summary>
    Yes, multiple users can have the same project open simultaneously in FMU Settings. However, to prevent conflicting changes, only one user can edit the project at a time. The project can be either editable or read-only. While one user is editing, others will have read-only access.  If the project is read-only, try <code>Enable editing</code>. If someone else is already editing, FMU Settings shows who currently holds the lock.
</details>

<details>
    <summary>Can I keep all settings in my global config and still use FMU Settings?</summary>
    If you have configured your project's master data in FMU Settings and still have one or more of these sections in your <code>global_master_config.yml</code> file, you should remove them (and the corresponding files in <code>/fmuconfig/input</code>):
    <ul>
    <li>model</li>
    <li>masterdata</li>
    <li>stratigraphy</li>
    <li>access</li> 
    </ul>
</details>

<details>
    <summary>I have just started using FMU Settings. What do I need to change in my FMU model to be able to run everything?</summary>
    First, you will have to make sure you have the <code>CREATE_CASE_METADATA</code> workflow in your ERT configuration file. This is a requirement for exporting metadata with fmu-dataio and FMU Settings.
    <br><br>
    Secondly, if you have configured your project's master data in FMU Settings and still have one or more of these sections in your <code>global_master_config.yml</code> file, you should remove them (and the corresponding files in <code>/fmuconfig/input</code>):
    <ul>
    <li>model</li>
    <li>masterdata</li>
    <li>stratigraphy</li>
    <li>access</li> 
    </ul>
    If you don't have these sections in your <code>global_master_config.yml</code> you do not need to change anything, you're good to go!
</details>


## Initialization and Getting Started
<details>
    <summary>Why is the list of projects to open empty?</summary>
    The dropdown list only shows recent projects. You can enter the project path manually and the GUI will then open the project, if it is already initialized, or offer to initialize it if needed. See the <a href="getting_started.html">Getting Started</a> page for instructions on how to initialize FMU Settings.
</details>

<details>
    <summary>Why is my project opened in read-only mode?</summary>
    When another user is actively working on a project, the project is locked to prevent simultaneous edits. In this case, the project opens in read-only mode for you:
    <ul>
    <li>You can view all project data.</li>
    <li>You cannot make edits or save changes while it’s locked.</li>
    <li> The FMU Settings panel displays who currently holds the lock.</li>
    </ul>
    Once the project is no longer in use by others and becomes available for editing, you will see an option to <code>Enable editing</code> on the Overview page on the left menu. Click this to gain full editing access.
    This locking behavior works similarly to the familiar RMS lock files, ensuring data integrity by preventing conflicting changes.
</details>

<details>
    <summary>Why can't I see my asset in the Sumo target asset list in FMU Settings?</summary>
    This can occur if your asset has not yet been onboarded to Sumo, or if it was only recently onboarded. Your asset will not appear in the asset list within FMU Settings until the next stable Komodo release. (This delay is not optimal and we plan to improve this process in a future update.)
</details>

## RMS Project
<details>
    <summary>What does it mean to access the RMS project from within FMU Settings?</summary>
    To edit the stratigraphy and the wellbores sections in FMU Settings you must establish the connection between FMU Settings and RMS, so that FMU Settings can read from it. Due to a limited number of RMS licenses and license limitations, RMS is not opened by default when FMU Settings is opened. When you access the RMS project you will have an open connection to RMS for two hours before the RMS connection will be automatically closed.
</details>


## Masterdata
<details>
    <summary>Why can't I see my field when I search for it?</summary>
    If your field is not available in the list, it means that your field is not in SMDA. To be able to map your project to official masterdata your field must exist in SMDA. See the <a href="overview.html">Overview</a> page to read more.
</details>

<details>
    <summary>Can I add a stratigraphic column from a neighboring field when my field does not have its own stratigraphic column?</summary>
    No. Adding a stratigraphic column from a neighboring field is not possible. To be able to add a stratigraphic column your field must have at least one stratigraphic column in SMDA.
</details>


## Mapping
<details>
    <summary>I have updated my stratigraphic framework in RMS. What do I need to do in FMU Settings to include the updated stratigraphy in my project?</summary>
    If you have made changes to the stratigraphic column in RMS you must open FMU Settings for your project, access the RMS project, and open the RMS Stratigraphy page. Add and/or remove horizons and zones accordingly. Any stored horizons or zones that are no longer present in RMS will be removed, together with their mappings, when you select <code>Save</code>. Map the newly added stratigraphy on the Mappings Stratigraphy page.
</details>

<details>
    <summary>I have added new wells to RMS. What do I need to do in FMU Settings to add the new wells to my project?</summary>
    If you have made changes to the wells in RMS you must open FMU Settings for your project, access the RMS project, and open the RMS Wellbores page. Add and/or remove wells accordingly. Any stored wellbores that are no longer present in RMS will be removed, together with their mappings, when you select <code>Save</code>. Map the newly added wellbores on the Mappings Wellbores page.
</details>

<details>
    <summary>Do I have to map my RMS wells to simulator wells to be able to visualize my wells in Webviz?</summary>
    No. Mapping wellbores between RMS and simulator is optional. If you want to upload RMS wells to Sumo (for instance to be able to visualize them in Webviz), the only mandatory step is to map the RMS well names to SMDA well names.
</details>


## Synchronization between projects
<details>
    <summary>I have made changes with FMU Settings in my user copy of the project. How can I merge these changes into the Master project?</summary>
    To copy FMU Settings from one revision to another, you can use the terminal command <code>fmu sync</code>. See the <a href="terminal_commands.html">Terminal Commands</a> page for instructions on how to use this.
</details>

<details>
    <summary>I merged FMU Settings from my user revision to the master revision by accident. What should I do to roll back to a previous version?</summary>
    If you have saved changes in FMU Settings, you will have previous versions stored as snapshots on the History page. Here you can select and restore a previous version (snapshot). The current version will then be overwritten by the snapshot version you have chosen.
</details>


## Access and Authentication
<details>
    <summary>Why do I have to log on and authenticate every time I want to make changes to my project's master data?</summary>
    You have to log on and authenticate to be able to access data in SMDA. 
</details>


## Troubleshooting
<details>
    <summary>I have edited something in my .fmu folder manually. Is there a way to get back a previous version?</summary>
    No, which is why users should never edit the content of .fmu manually.
</details>

<details>
    <summary>When I open FMU Settings it seems to be an empty project and it shows an error message saying "Network error". What is wrong?</summary>
    If you get an empty project and a network error when opening FMU Settings, try performing a hard refresh of your browser (Ctrl + Shift + R)
</details>

<details>
    <summary>My ERT run is completed but nothing seems to be uploaded to Sumo. What could be wrong?</summary>
    To generate and export metadata using fmu-dataio and FMU Settings, your ERT configuration file must include the <code>WF_CREATE_CASE_METADATA</code> workflow. If this workflow is not executed, fmu-dataio will be unable to export metadata, and without metadata, the data will not be uploaded to Sumo.
</details>

