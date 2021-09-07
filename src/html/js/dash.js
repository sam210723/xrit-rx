'use strict';
/**
 *  dash.js
 *  https://github.com/sam210723/xrit-rx
 *  
 *  Updates dashboard data using xrit-rx API
 */

var config = {};
var blocks = {
    demod:    {
        width: 390,
        height: 180,
        title: "Demodulator Status",
        update: block_demod
    },
    decoder:    {
        width: 620,
        height: 180,
        title: "Decoder Status",
        update: block_decoder
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
var current_progress;
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
    var header = document.getElementById("navbar");
    var title = document.createElement("span");
    var version = document.createElement("span");    
    var link = document.createElement("a");
    title.id = "navbar-title";
    title.innerText = `${config.spacecraft} ${config.downlink} Dashboard`;
    version.id = "navbar-version";
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
                    new_version.id = "navbar-version-new";
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
    // Get current status of xrit-rx
    http_get("/api/status", (res) => {
        if (res.status == 200) {
            res.json().then((data) => {
                current_vcid = data['vcid'];
                current_progress = data['progress'];
                latest_image = data['image'];
            });
        }
        else {
            print("Failed to poll API", "POLL");
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
    
    // Create clock elements
    var clocks = document.createElement("div");
    var local = document.createElement("div");
    var utc = document.createElement("div");
    clocks.className = "schedule-clocks";
    local.style.float = "left";
    local.className = "schedule-clocks-clock";
    utc.style.float = "right";
    utc.className = "schedule-clocks-clock";
    
    // Add clocks to document
    clocks.appendChild(local);
    clocks.appendChild(utc);
    element.appendChild(clocks);
}


/**
 * Update Demodulator Status block
 */
function block_demod(element)
{
    // Check block has been built
    if (element.innerHTML == "") {
        var locked = document.createElement("span");
        locked.className = "indicator";
        locked.id = "demod-locked"
        locked.title = "Demodulator lock state";
        locked.innerHTML = "<span>LOCK</span><p>GK-2A LRIT</p>";
        locked.style = "float: left;";
        locked.setAttribute("active", "");
        element.appendChild(locked);

        var offset = document.createElement("span");
        offset.id = "demod-offset"
        offset.title = "Demodulator frequency offset:";
        offset.innerHTML = "<b>Frequency:</b> -1.25 kHz";
        offset.style = "float: left; margin: 2px 0 13px 20px;";
        element.appendChild(offset);

        var viterbi = document.createElement("span");
        viterbi.id = "demod-viterbi";
        viterbi.title = "Demodulator Viterbi error count";
        viterbi.innerHTML = "<b>Viterbi Errors:</b> 24";
        viterbi.style = "float: left; margin: 2px 0 13px 20px;";
        element.appendChild(viterbi);
        element.innerHTML += "<br>";

        var rs = document.createElement("span");
        rs.id = "demod-rs"
        rs.title = "Demodulator Reed-Solomon error count";
        rs.innerHTML = "<b>Reed-Solomon:</b> 0";
        rs.style = "float: left; margin: 2px 0 13px 20px;";
        element.appendChild(rs);
    }
    else {  // Update block
        
    }
}


/**
 * Update Decoder Status block
 */
function block_decoder(element)
{
    // Check block has been built
    if (element.innerHTML == "") {
        for (var ch in vchans[config.spacecraft]) {
            var indicator = document.createElement("span");
            indicator.className = "progress";
            indicator.id = `vcid-${ch}`
            indicator.title = vchans[config.spacecraft][ch][1];

            var name = vchans[config.spacecraft][ch][0];
            indicator.innerHTML = `<div class="progress-text"><span>${name}</span><p>VCID ${ch}</p></div><div class="progress-bar">&nbsp;</div>`;

            // Set 'disabled' attribute on ignored VCIDs
            if (config.ignored.indexOf(parseInt(ch)) > -1) {
                indicator.setAttribute("disabled", "");
                indicator.title += " (ignored)";
            }

            element.appendChild(indicator);
        }
    }
    else {  // Update block
        for (var ch in vchans[config.spacecraft]) {
            // Do not update ignored channels
            if (config.ignored.indexOf(parseInt(ch)) > -1) { continue; }

            // Update active channel
            if (ch == current_vcid) {
                document.getElementById(`vcid-${ch}`).setAttribute("active", "");
                document.getElementById(`vcid-${ch}`).children[1].style.width = `${current_progress}%`;
            }
            else {
                document.getElementById(`vcid-${ch}`).removeAttribute("active");
                document.getElementById(`vcid-${ch}`).children[1].style.width = "0";
            }
        }
    }
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

        var fname = latest_image.split('/')[2];
        var ext = fname.split('.')[1];
        fname = fname.split('.')[0];

        // Set <img> src attribute
        if (ext != "txt") {
            // Only update image element if URL has changed
            if (img.getAttribute("src") != url) {
                img.setAttribute("src", url);
                link.setAttribute("href", url);
                cap.innerText = fname.replace("_ENHANCED", "");
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
        // Reload page at UTC midnight to get updated schedule
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
    for (var i = first; i < first + 9; i++) {
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

    // Update clocks
    var local = element.children[1].children[0];
    var utc = element.children[1].children[1];
    local.innerHTML = `<div class="schedule-clocks-clock-time">${get_time_local()}</div><div class="schedule-clocks-clock-zone" title="UTC${get_time_utc_offset()}">Local</div>`;
    utc.innerHTML = `<div class="schedule-clocks-clock-time">${get_time_utc()}</div><div class="schedule-clocks-clock-zone">UTC</div>`;
}
