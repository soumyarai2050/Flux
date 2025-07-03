import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import { FileOptions } from '../core/schemaConstants';

const LOCAL_TZ = Intl.DateTimeFormat().resolvedOptions().timeZone;

dayjs.extend(utc);
dayjs.extend(timezone);


/**
 * Converts an integer timestamp (assumed to be UTC) into a Day.js object with a specified timezone.
 * The target timezone is determined by `FileOptions.date_time_print_timezone`.
 * If `FileOptions.date_time_print_timezone` is 'LOCAL', the local system's timezone is used.
 * Otherwise, the specified timezone from `FileOptions` is applied.
 * @param {number} value - The integer timestamp to convert.
 * @returns {dayjs.Dayjs} A Day.js object representing the date and time in the target timezone.
 */
export function getDateTimeFromInt(value) {
    // Create a Day.js object from the integer value, assuming it's in UTC.
    const dateTime = dayjs(value).utc();
    let dateTimeWithTimezone;

    // Apply the appropriate timezone based on FileOptions.
    if (FileOptions.date_time_print_timezone === 'LOCAL') {
        // Use the local system's timezone.
        dateTimeWithTimezone = dateTime.tz(LOCAL_TZ);
    } else {
        // Use the timezone specified in FileOptions.
        dateTimeWithTimezone = dateTime.tz(FileOptions.date_time_print_timezone);
    }
    return dateTimeWithTimezone;
}
