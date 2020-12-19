'use strict';

/**
 * Print timestamped and sourced message to console
 * @param {string} msg Message to print
 * @param {string} src Message source identifier
 */
function print(msg, src=false)
{
    var now = new Date();
    var h = now.getHours().toString().padStart(2, "0");
    var m = now.getMinutes().toString().padStart(2, "0");
    var s = now.getSeconds().toString().padStart(2, "0");
    var ms = now.getMilliseconds().toString().padStart(3, "0");
    var time = `${h}:${m}:${s}.${ms}`;

    var out = `[${time}]`;
    if (src) { out += ` [${src}]`; }
    out += `  ${msg}`;

    console.log(out);
}


/**
 * Returns local time as string
 */
function get_time_local()
{
    var d = new Date();

    var hours = d.getHours().toString().padStart(2, '0');
    var mins = d.getMinutes().toString().padStart(2, '0');
    var secs = d.getSeconds().toString().padStart(2, '0');

    return `${hours}:${mins}:${secs}`;
}


/**
 * Returns UTC time as string
 */
function get_time_utc()
{
    var d = new Date();

    var hours = d.getUTCHours().toString().padStart(2, '0');
    var mins = d.getUTCMinutes().toString().padStart(2, '0');
    var secs = d.getUTCSeconds().toString().padStart(2, '0');

    return `${hours}:${mins}:${secs}`;
}


/**
 * Returns timezone offset relative to UTC
 */
function get_time_utc_offset()
{
    var d = new Date();
    var offset = d.getTimezoneOffset() / 60;

    if (Math.sign(offset) == -1) {
        return `+${Math.abs(offset)}`;
    }
    else {
        return `-${Math.abs(offset)}`;
    }
}


/**
 * Returns time until the specified timestamp as string
 */
function get_time_until(target)
{
    var difference = target - new Date();
    
    var h = Math.floor( (difference/(1000*60*60)) % 24 );
    var m = Math.floor( (difference/1000/60) % 60 );
    var s = Math.floor( (difference/1000) % 60 );

    var remaining = "";
    remaining += h != 0 ? `${h}h ` : "";
    remaining += m != 0 ? `${m}m ` : "";
    remaining += `${s}s`;

    if ((h == 23 && m == 59) || (h == 0 && m == 0 && s == 0)) {
        return 0;
    }
    else {
        return remaining;
    }
}

/**
 * Parses KMA DOP into JSON object
 * @param {Array} raw Raw KMA DOP
 */
function parse_schedule(raw)
{
    var start = -1;
    var end = -1;

    // Get DOP date
    var dop_date = new Date(raw[2].replace("DISSEMINATION SCHEDULE FROM ", ""));
    print(`DOP Date: ${dop_date.getUTCDate() + 1}-${dop_date.getUTCMonth() + 1}-${dop_date.getUTCFullYear()}`, "SCHD");

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

    return sch;
}


/**
 * Send HTTP GET request to specified URL
 * @param {string} url URL to retrieve
 * @param {function} callback Function to call on response
 */
function http_get(url, callback)
{
    /* Fetch API */
    fetch(url)
        .then(callback)
        .catch(function(err) {
            print(`Error getting \"${url}\": ${err}`, "HTTP");
            callback(false);
        });
}
