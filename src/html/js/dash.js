function init()
{
    print("Starting xrit-rx dashboard...", "DASH");

    configure();
}


/**
 * Configure dashboard elements
 */
function configure()
{
    print("Getting dashboard configuration...","CONF");
    
    config = JSON.parse(http_get("/api"))
    console.log(config);
}
