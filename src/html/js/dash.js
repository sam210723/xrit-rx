/**
 *  dash.js
 *  https://github.com/sam210723/xrit-rx
 *  
 *  Updates dashboard data through xrit-rx REST API
 */

var config = {};

function init()
{
    print("Starting xrit-rx dashboard...", "DASH");

    // Configure dashboard
    ok = configure();
    if (!ok) { return; }
    
    print("Ready", "DASH");
}


/**
 * Configure dashboard
 */
function configure()
{
    print("Getting dashboard configuration...","CONF");

    // Get config object from xrit-rx
    res = http_get("/api");
    if (res) {
        config = JSON.parse(res);
    }
    else {
        print("Failed to get configuration", "CONF");
        return false;
    }

    // Write config object to console
    console.log(config);

    return true;
}

}
