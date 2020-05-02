'use strict';
/**
 *  dash.js
 *  https://github.com/sam210723/xrit-rx
 *  
 *  Updates dashboard data through xrit-rx API
 */

var config = {};
var blocks = {
    vchan:    {
        width: 620,
        height: 180,
        title: "Virtual Channel",
        update: block_vchan
    },
    time:     {
        width: 390,
        height: 180,
        title: "Time",
        update: block_time
    },
    lastimg:  {
        width: 500,
        height: 590,
        title: "Last Image",
        update: block_lastimg
    },
    schedule: {
        width: 510,
        height: 590,
        title: "Schedule",
        update: block_schedule
    }
};
var vchans = {
    "GK-2A": {
        0:  ["FD", "Full Disk"],
        4:  ["ANT", "Alpha-numeric Text"],
        5:  ["ADD", "Additional Data"],
        63: ["IDLE", "Fill Data"]
    }
};
var sch = [];
var current_vcid;
var last_image;

function init()
{
    print("Starting xrit-rx dashboard...", "DASH");

    // Configure dashboard
    if (!configure()) { return; }
    
    print("Ready", "DASH");
}


/**
 * Configure dashboard
 */
function configure()
{
    print("Getting dashboard configuration...","CONF");

    // Get config object from xrit-rx
    var res = http_get("/api");
    if (res) {
        config = JSON.parse(res);
    }
    else {
        print("Failed to get configuration", "CONF");
        return false;
    }

    // Write config object to console
    console.log(config);

    // Set heading and window title
    var heading = document.getElementById("dash-heading");
    heading.innerHTML = `${config.spacecraft} ${config.downlink} Dashboard <span>xrit-rx v${config.version}</span>`;
    document.title = `${config.spacecraft} ${config.downlink} - xrit-rx v${config.version}`;

    // Build blocks
    console.log(blocks);
    for (var block in blocks) {
        var el = document.getElementById(`block-${block}`);
        blocks[block].body = el.children[1];
        
        // Set block size
        el.style.width  = `${blocks[block].width}px`;
        el.style.height = `${blocks[block].height}px`;

        // Set block heading
        el.children[0].innerText = blocks[block].title;
    }

    // Parse and build schedule
    if (config.spacecraft == "GK-2A") { schedule() };

    // Setup polling loop
    setInterval(poll, config.interval * 1000);

    // Initial poll() call
    poll();
    poll();

    return true;
}


/**
 * Poll xrit-rx API for updated data
 */
function poll()
{
    // Get current VCID
    var res = http_get("/api/current/vcid");
    if (res) {
        current_vcid = JSON.parse(res)['vcid'];
    }
    else {
        print("Failed to get current VCID", "POLL");
        return false;
    }

    // Get last image
    var res = http_get("/api/last/image");
    if (res) {
        last_image = JSON.parse(res)['image'];
    }
    else {
        print("Failed to get last image", "POLL");
        return false;
    }

    // Call update function for each block
    for (var block in blocks) {
        blocks[block].update(blocks[block].body);
    }
}

/**
 * Download, parse and build schedule table
 */
function schedule()
{
    // Get UTC date
    var d = new Date();
    var date = `${d.getUTCFullYear()}${(d.getUTCMonth()+1).toString().padStart(2, "0")}${d.getUTCDate().toString().padStart(2, "0")}`;

    // Build request URL
    var url = "https://vksdr.com/scripts/kma-dop.php";
    var params = `?searchDate=${date}&searchType=${config.downlink}`;

    // Setup XHTTP object
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            var element = document.getElementById("block-schedule").children[1];
            element.style.height = `${blocks.schedule.height-90}px`;

            var raw = JSON.parse(this.responseText)["data"];
            var start = -1;
            var end = -1;

            // Find start and end of DOP
            for (var i in raw) {
                var line = raw[i].trim();

                if (line.startsWith("TIME(UTC)")) {
                    start = parseInt(i) + 1;
                }

                if (line.startsWith("ABBREVIATIONS:")) {
                    end = parseInt(i) - 2;
                }
            }

            // Loop through schedule entries
            for (var i = start; i <= end; i++) {
                var line = raw[i].trim().split('\t');
                var entry = [];

                entry[0] = line[0].substring(0, line[0].indexOf("-"));
                entry[1] = line[0].substring(line[0].indexOf("-") + 1);
                entry[2] = line[1].substring(0, line[1].length - 3);
                entry[3] = line[1].substring(line[1].length - 3);
                entry[4] = line[2];
                entry[5] = line[3] == "O";

                if (entry[2] == "EGMSG") { continue; }   // Skip EGMSG

                sch.push(entry);
            }
            
            var table = document.createElement("table");
            table.className = "schedule";

            // Table header
            var header = table.createTHead();
            var row = header.insertRow(0);
            row.insertCell(0).innerHTML = "Start (UTC)";
            row.insertCell(1).innerHTML = "End (UTC)";
            row.insertCell(2).innerHTML = "Type";
            row.insertCell(3).innerHTML = "ID";

            // Schedule entries
            var body = table.appendChild(document.createElement("tbody"));
            for (var i in sch) {
                var  row = body.insertRow();

                var start = `${sch[i][0].substr(0, 2)}:${sch[i][0].substr(2, 2)}:${sch[i][0].substr(4, 2)}`
                var end = `${sch[i][1].substr(0, 2)}:${sch[i][1].substr(2, 2)}:${sch[i][1].substr(4, 2)}`

                row.insertCell().innerHTML = start;
                row.insertCell().innerHTML = end;
                row.insertCell().innerHTML = sch[i][2];
                row.insertCell().innerHTML = sch[i][3];
            }

            // Add table to document
            element.innerHTML = "";
            element.appendChild(table);

            print("Ready", "SCHD");
        }
    };

    // Download raw schedule
    xhttp.open("GET", url + params, true);
    xhttp.send();
}


/**
 * Update Virtual Channel block
 */
function block_vchan(element)
{
    // Check block has been built
    if (element.innerHTML == "") {
        for (var ch in vchans[config.spacecraft]) {
            var indicator = document.createElement("span");
            indicator.className = "vchan";
            indicator.id = `vcid-${ch}`
            indicator.title = vchans[config.spacecraft][ch][1];

            var name = vchans[config.spacecraft][ch][0];
            indicator.innerHTML = `<span>${name}</span><p>VCID ${ch}</p>`;

            // Set 'disabled' attribute on blacklisted VCIDs
            if (config.vcid_blacklist.indexOf(parseInt(ch)) > -1) {
                indicator.setAttribute("disabled", "");
                indicator.title += " (blacklisted)";
            }

            element.appendChild(indicator);
        }
    }
    else {  // Update block
        for (var ch in vchans[config.spacecraft]) {
            // Do not update blacklisted channels
            if (config.vcid_blacklist.indexOf(parseInt(ch)) > -1) { continue; }

            // Update active channel
            if (ch == current_vcid) {
                document.getElementById(`vcid-${ch}`).setAttribute("active", "");
            }
            else {
                document.getElementById(`vcid-${ch}`).removeAttribute("active");
            }
        }
    }
}


/**
 * Update Time block
 */
function block_time(element)
{
    var local = element.children[0];
    var utc = element.children[1];

    local.innerHTML = `${get_time_local()}<br><span title="UTC ${get_time_utc_offset()}">Local</span>`;
    utc.innerHTML = `${get_time_utc()}<br><span>UTC</span>`;
}


/**
 * Update Last Image block
 */
function block_lastimg(element)
{
    if (last_image) {
        var url = `/api/${last_image}`;
        var fname = url.split('/');
        fname = fname[fname.length - 1];
        var ext = fname.split('.')[1];
        fname = fname.split('.')[0];

        // Set <img> src attribute
        if (ext != "txt") {
            element.children[0].innerHTML = `<img class="lastimg" src="${url}" />`;
            element.children[0].setAttribute("href", url);    
        }
        
        // Set image file name caption
        element.children[2].innerText = fname;
    }
    else {
        element.children[2].innerText = "Waiting for image...";
    }
}


/**
 * Update Schedule block
 */
function block_schedule(element)
{
    if (sch.length == 0) { return; }    // Check schedule has been loaded

    // Get schedule table cells as list
    var cells = element.children[0].children[1].children;

    // Get current UTC time
    var time = get_time_utc().replace(/:/g, "");

    // Check block has been built
    if (element.innerHTML != "") {
        for (var entry in sch) {
            var start = sch[entry][0];
            var end = sch[entry][1];

            if (entry == sch.length-1) { continue; }

            if (time > start) {
                cells[entry].removeAttribute("active", "");
                cells[entry].setAttribute("disabled", "");
                cells[entry].scrollIntoView();
                element.scrollTop -= 100;

            }

            if (time > start && time < end) {
                cells[entry].removeAttribute("disabled", "");
                cells[entry].setAttribute("active", "");
            }
        }
    }
}
