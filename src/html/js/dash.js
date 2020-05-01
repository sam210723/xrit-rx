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
}
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

    local.innerHTML = `${get_time_local()}<br><span title="UTC${get_time_utc_offset()}">LOCAL</span>`;
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
    
}
