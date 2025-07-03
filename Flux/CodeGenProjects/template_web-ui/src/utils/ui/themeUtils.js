import { DATA_TYPES } from '../../constants';
import { Theme } from '../../theme';

export function getDataSourceColor(theme, dataSourceIndex, joinKey = false, commonGroupKey = false, overrideColor = null) {
    if (joinKey) {
        return theme.palette.primary.dark;
    } else if (commonGroupKey) {
        return theme.palette.primary.light;
    }
    if (overrideColor && overrideColor.startsWith('#')) {
        let updatedOverrideColor = overrideColor;
        if (overrideColor.length === 4) {
            updatedOverrideColor = '#';
            for (let i = 1; i < overrideColor.length; i++) {
                updatedOverrideColor += `${overrideColor[i]}${overrideColor[i]}`;
            }
        }
        if (!/^#[0-9A-F]{6}$/i.test(updatedOverrideColor)) {
            throw new Error('Invalid base color format');
        } else {
            return updatedOverrideColor;
        }
    }
    let baseColor = theme.palette.background.primary;
    if (typeof baseColor === DATA_TYPES.STRING) {
        baseColor = baseColor.toUpperCase();
        if (baseColor.length === 4) {
            let updatedBaseColor = '#';
            for (let i = 1; i < baseColor.length; i++) {
                updatedBaseColor += `${baseColor[i]}${baseColor[i]}`;
            }
            baseColor = updatedBaseColor;
        }
    }
    let stepSize;
    if (theme.palette.mode === Theme.DARK) {
        stepSize = 20;
    } else {
        stepSize = -20;
    }
    const updatedColor = getColorByIndex(baseColor, dataSourceIndex, stepSize);
    return updatedColor;
}

function getColorByIndex(baseColor, index, stepSize) {
    // Ensure index is non-negative
    if (index < 0) {
        throw new Error('Index must be non-negative');
    }

    // Ensure baseColor is in the format '#RRGGBB'
    if (!/^#[0-9A-F]{6}$/i.test(baseColor)) {
        throw new Error('Invalid base color format');
    }

    // Extract RGB components
    const red = parseInt(baseColor.substring(1, 3), 16);
    const green = parseInt(baseColor.substring(3, 5), 16);
    const blue = parseInt(baseColor.substring(5, 7), 16);

    const stepIndex = index / 3;
    const stepModulo = index % 3;

    let updatedRed;
    let updatedGreen;
    let updatedBlue;
    if (stepSize >= 0) {
        updatedRed = Math.min(red + (stepSize * stepIndex), 255);
        updatedGreen = Math.min(green + (stepSize * stepIndex), 255);
        updatedBlue = Math.min(blue + (stepSize * stepIndex), 255);

        if (stepModulo === 1) {
            updatedGreen = Math.min(updatedGreen + (stepSize * 1), 255);
        } else if (stepModulo === 2) {
            updatedBlue = Math.min(updatedBlue + (stepSize * 1), 255);
        }
    } else {  //  step size is negative
        updatedRed = Math.max(red + (stepSize * stepIndex), 0);
        updatedGreen = Math.max(green + (stepSize * stepIndex), 0);
        updatedBlue = Math.max(blue + (stepSize * stepIndex), 0);

        if (stepModulo === 1) {
            updatedGreen = Math.max(updatedGreen + (stepSize * 1), 0);
        } else if (stepModulo === 2) {
            updatedBlue = Math.max(updatedBlue + (stepSize * 1), 0);
        }
    }
    updatedRed = Math.floor(updatedRed);
    updatedGreen = Math.floor(updatedGreen);
    updatedBlue = Math.floor(updatedBlue);

    // Convert reduced RGB components back to hexadecimal
    const finalColor = `#${updatedRed.toString(16).padStart(2, '0')}${updatedGreen.toString(16).padStart(2, '0')}${updatedBlue.toString(16).padStart(2, '0')}`;
    return finalColor;
}