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
        update: null
    },
    latestimg:  {
        width: 500,
        height: 590,
        title: "Latest Image",
        update: block_latestimg
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
var sch_offline = false;
var current_vcid;
var latest_image;
var utc_date;

function init()
{
    print("Starting xrit-rx dashboard...", "DASH");

    // Get config object from xrit-rx
    http_get("/api", (res) => {
        if (res.status == 200) {
            res.json().then((data) => {
                config = data;
                
                // Configure dashboard
                if (!configure()) { return; }
                print("Ready", "DASH");
            })
        }
        else {
            print("Failed to get configuration", "CONF");
            return false;
        }
    });
}


/**
 * Configure dashboard
 */
function configure()
{
    // Write config object to console
    console.log(config);

    // Set dashboard title
    document.title = `${config.spacecraft} ${config.downlink} - xrit-rx v${config.version}`;

    // Build dashboard header
    var header = document.getElementById("dash-header");
    var title = document.createElement("span");
    var version = document.createElement("span");    
    var link = document.createElement("a");
    title.id = "dash-header-title";
    title.innerText = `${config.spacecraft} ${config.downlink} Dashboard`;
    version.id = "dash-header-version";
    version.innerText = `xrit-rx `;
    link.href = `https://github.com/sam210723/xrit-rx/releases/tag/v${config.version}`;
    link.target = "_blank";
    link.title = "Release notes on GitHub";
    link.innerText = `v${config.version}`;
    version.appendChild(link);
    header.appendChild(title);
    header.appendChild(version);

    // Check for newer version on GitHub
    http_get("https://api.github.com/repos/sam210723/xrit-rx/releases/latest", (res) => {
        if (res.status == 200) {
            res.json().then((data) => {
                if (`v${config.version}` != data["tag_name"]) {
                    var new_version = document.createElement("a");
                    new_version.id = "dash-header-version-new";
                    new_version.title = `A new version of xrit-rx is available on GitHub`;
                    new_version.innerText = `Download ${data["tag_name"]}`;
                    new_version.href = "https://github.com/sam210723/xrit-rx/releases/latest";
                    new_version.target = "_blank";
                    header.appendChild(new_version);
                    
                    print(`New version available on GitHub (${data["tag_name"]})`, "DASH");
                }
                else {
                    print(`Running latest version of xrit-rx`, "DASH");
                }
            });
        }
        else {
            print("Failed to get latest release version", "DASH");
        }
    });

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
    if (config.spacecraft == "GK-2A") { get_schedule() };

    // Setup clock loop
    setInterval(() => {
        block_time(blocks.time.body);
    }, 100);
    block_time(blocks.time.body);

    // Setup polling loop
    setInterval(poll, config.interval * 1000);
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
    http_get("/api/current/vcid", (res) => {
        if (res.status == 200) {
            res.json().then((data) => {
                current_vcid = data['vcid'];
            });
        }
        else {
            print("Failed to get current VCID", "POLL");
            return false;
        }
    });

    // Get last image
    http_get("/api/latest/image", (res) => {
        if (res.status == 200) {
            res.json().then((data) => {
                latest_image = data['image'];
            });
        }
        else {
            print("Failed to get last image", "POLL");
            return false;
        }
    });

    // Call update function for each block
    for (var block in blocks) {
        if (blocks[block].update != null) {
            blocks[block].update(blocks[block].body);
        }
    }
}


/**
 * Download and parse schedule
 */
function get_schedule()
{
    sch = [];
    var element = blocks['schedule'].body;
    element.innerHTML = `<p class="loader">Downloading schedule...</p>`;

    // Get UTC date
    var d = new Date();
    utc_date = `${d.getUTCFullYear()}${(d.getUTCMonth()+1).toString().padStart(2, "0")}${d.getUTCDate().toString().padStart(2, "0")}`;

    /**
     * Schedule download is proxied through my web server at vksdr.com because KMA 
     * have not included CORS headers in their API. Mordern browsers will disallow 
     * cross-domain requests unless these headers are present. The PHP backend of 
     * my web server will make the request to the KMA API then return the result to 
     * the dashboard with the necesary CORS headers.
     * 
     * See https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
     */

    // Build request URL
    var url = "https://vksdr.com/scripts/kma-dop.php";
    var params = `?searchDate=${utc_date}&searchType=${config.downlink}`;

    // Get online schedule
    http_get(url + params, (res) => {
        if (res.status == 200) {
            res.json().then((data) => {
                sch = parse_schedule(data['data']);
                
                print("Ready (online)", "SCHD");
            });
        }
        else {
            print("Failed to get online schedule", "SCHD");
            
            http_get("/schedule.txt", (res) => {
                if (res.status == 200) {
                    res.text().then((data) => {
                        data = data.split('\n');
                        sch = parse_schedule(data);

                        if (sch) {
                            print("Ready (offline)", "SCHD");
                            sch_offline = true;
                        }
                        else {
                            print("Offline schedule is stale", "SCHD");

                            return false;
                        }
                    });
                }
                else {
                    print("Failed to get offline schedule", "SCHD");
                    sch = false;

                    return false;
                }
            });
        }
    });
}


/**
 * Build schedule table DOM element
 */
function build_schedule()
{
    // Create schedule table
    var table = document.createElement("table");
    table.className = "schedule";
    table.appendChild(document.createElement("tbody"));

    // Table header
    var header = table.createTHead();
    var row = header.insertRow(0);
    var headings = ["Start (UTC)", "End (UTC)", "Type", "ID"];
    for (var h in headings)
    {
        var th = document.createElement("th");
        th.innerText = headings[h];
        row.appendChild(th);

    }

    // Add table to document
    var element = blocks['schedule'].body;
    element.innerHTML = "";
    element.appendChild(table);
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
 * Update Latest Image block
 */
function block_latestimg(element)
{
    var img = element.children[0].children[0];
    var link = element.children[0];
    var cap = element.children[2];

    if (latest_image) {
        var url = `/api/received/${latest_image}`;
        var fname = url.split('/');
        fname = fname[fname.length - 1];
        var ext = fname.split('.')[1];
        fname = fname.split('.')[0];

        // Set <img> src attribute
        if (ext != "txt") {
            // Only update image element if URL has changed
            if (img.getAttribute("src") != url) {
                img.setAttribute("src", url);
                link.setAttribute("href", url);
                cap.innerText = fname;
            }
        }
    }
    else {
        // Check image output is enabled
        if (config.images == false) {
            cap.innerHTML = "Image output is disabled in xrit-rx<br><br>Check key file is present and <code>images = true</code> in <code>xrit-rx.ini</code> configuration file";
        }
        else {
            link.innerHTML = "<img class=\"latestimg\">";
            link.setAttribute("href", "#");
            cap.innerText = "Waiting for image...";
        }
    }
}


/**
 * Update Schedule block
 */
function block_schedule(element)
{
    // Check schedule has been loaded
    if (sch.length == 0) { return; }

    // If schedule failed to download
    if (!sch) {
        // Calculate time until next schedule is transmitted
        var schedule_time = new Date();
        schedule_time.setUTCHours(3, 29, 15);
        schedule_time.setUTCDate(schedule_time.getUTCDate() + 1);
        var time_remaining = get_time_until(schedule_time);

        if (time_remaining == 0) {
            time_remaining = "<b>right now</b>";
        }
        else {
            time_remaining = `in <b>${time_remaining}</b>`;
        }

        element.innerHTML = "" +
            `<p>Failed to download online ${config.downlink} schedule from ` +
            `<a href="https://nmsc.kma.go.kr/enhome/html/satellite/plan/selectDailyOperPlan.do" target="_blank">KMA NMSC</a><br>` +
            `<button onclick="get_schedule()">Retry download</button></p><br><br><br><br>` +
            `<p><h3>Offline Schedule</h3>` +
            `Each day a schedule is transmitted via the ${config.downlink} downlink at 03:29:15 UTC. ` +
            `It will be displayed here once received.</p>` +
            `<p>Next schedule expected ${time_remaining}</p>`;
        
        return;
    }

    // Add spacecraft and downlink to block header
    var header = element.parentNode.children[0];
    header.innerHTML = `${config.spacecraft} ${config.downlink} Schedule`;
    if (sch_offline) header.innerHTML += `<div id="schedule-status" title="Using schedule received via ${config.downlink} downlink">OFFLINE</div>`;

    // Check UTC date
    var d = new Date();
    if (utc_date != `${d.getUTCFullYear()}${(d.getUTCMonth()+1).toString().padStart(2, "0")}${d.getUTCDate().toString().padStart(2, "0")}`) {
        location.reload();
    }
    
    // Get current UTC time
    var time = get_time_utc().replace(/:/g, "");

    // Find first entry to add to table
    var first;
    for (var entry in sch) {
        var start = sch[entry][0];
        var end = sch[entry][1];

        if (time < start) {
            first = Math.max(0, parseInt(entry) - 3);
            break;
        }
    }

    // Loop through schedule items
    build_schedule();
    var body = element.children[0].children[1];
    body.innerHTML = "";
    for (var i = first; i < first + 12; i++) {
        // Limit index
        if (i >= sch.length) { break; }

        var start = sch[i][0];
        var end = sch[i][1];
        var row = body.insertRow();

        // Add cells to row
        row.insertCell().innerHTML = `${sch[i][0].substr(0, 2)}:${sch[i][0].substr(2, 2)}:${sch[i][0].substr(4, 2)}`;
        row.insertCell().innerHTML = `${sch[i][1].substr(0, 2)}:${sch[i][1].substr(2, 2)}:${sch[i][1].substr(4, 2)}`;
        row.insertCell().innerHTML = sch[i][2];
        row.insertCell().innerHTML = sch[i][3];

        // Set past entries as disabled (except last entry)
        if (time > start && i != sch.length - 1) {
            row.removeAttribute("active", "");
            row.setAttribute("disabled", "");
        }

        // Set current entry as active
        if (time > start && time < end) {
            row.removeAttribute("disabled", "");
            row.setAttribute("active", "");
        }
    }
}
