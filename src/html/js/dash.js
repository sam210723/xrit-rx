'use strict';
/**
 *  dash.js
 *  https://github.com/sam210723/xrit-rx
 *  
 *  Updates dashboard data through xrit-rx API
 */

var config = {};

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

    // Setup polling loop
    setInterval(poll, config.interval * 1000);

    return true;
}


/**
 * Poll xrit-rx API for updated data
 */
function poll()
{
    
}
