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
        });
}
