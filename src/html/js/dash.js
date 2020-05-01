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
        height: 200,
        title: "Virtual Channel",
        update: block_vchan
    },
    time:     {
        width: 390,
        height: 200,
        title: "Time",
        update: block_time
    },
    lastimg:  {
        width: 500,
        height: 530,
        title: "Last Image",
        update: block_lastimg
    },
    schedule: {
        width: 510,
        height: 530,
        title: "Schedule",
        update: block_schedule
    }
};

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
    heading.innerHTML = `${config.spacecraft} ${config.downlink} <span>xrit-rx v${config.version}</span>`;
    document.title = `${config.spacecraft} ${config.downlink} - xrit-rx v${config.version}`;

    // Build blocks
    console.log(blocks);
    for (var block in blocks) {
        var el = document.getElementById(`block-${block}`);
        
        // Set block size
        el.style.width  = `${blocks[block].width}px`;
        el.style.height = `${blocks[block].height}px`;

        // Set block heading
        el.children[0].innerText = blocks[block].title;
    }

    // Setup polling loop
    setInterval(poll, config.interval * 1000);

    return true;
}


/**
 * Poll xrit-rx API for updated data
 */
function poll()
{
    // Call update function for each block
    for (var block in blocks) {
        blocks[block].update();
    }
}


/**
 * Update Virtual Channel block
 */
function block_vchan()
{
    
}


/**
 * Update Time block
 */
function block_time()
{
    
}


/**
 * Update Last Image block
 */
function block_lastimg()
{
    
}


/**
 * Update Schedule block
 */
function block_schedule()
{
    
}
