import { createTheme } from '@mui/material/styles';

export const Theme = {
    LIGHT: 'light',
    DARK: 'dark'
};

export const BaseColor = {
    GREEN: 'green',
    BLUE: 'blue',
    BROWN: 'brown'
};

// Global constant to control the default base color
// Change this value to BaseColor.BLUE or BaseColor.BROWN to change the app-wide default
export const DEFAULT_BASE_COLOR = BaseColor.BROWN;

export function cssVar(name) {
    if (typeof window !== 'undefined' && typeof document !== 'undefined') {
        const value = getComputedStyle(document.documentElement).getPropertyValue(name);
        if (value) {
            return value.trim();
        }
    }
}

const typography = {
    "fontFamily": `"Roboto", "Helvetica", "Arial", sans-serif`,
    "fontSize": 11,
    "fontWeightLight": 300,
    "fontWeightRegular": 500,
    "fontWeightMedium": 500
};

export const baseColorPalettes = {
    [BaseColor.GREEN]: {
        lightest: '--green-theme-lightest',
        lighter: '--green-theme-lighter',
        light: '--green-theme-light',
        medium: '--green-theme-medium',
        dark: '--green-theme-dark',
        darker: '--green-theme-darker',
        darkest: '--green-theme-darkest',
        contrasting: '--green-theme-accent',
    },
    [BaseColor.BLUE]: {
        lightest: '--blue-theme-lightest',
        lighter: '--blue-theme-lighter',
        light: '--blue-theme-light',
        medium: '--blue-theme-medium',
        dark: '--blue-theme-dark',
        darker: '--blue-theme-darker',
        darkest: '--blue-theme-darkest',
        contrasting: '--blue-theme-accent',
    },
    [BaseColor.BROWN]: {
        lightest: '--brown-theme-lightest',
        lighter: '--brown-theme-lighter',
        light: '--brown-theme-light',
        medium: '--brown-theme-medium',
        dark: '--brown-theme-dark',
        darker: '--brown-theme-darker',
        darkest: '--brown-theme-darkest',
        contrasting: '--brown-theme-accent',
    }
};

const getColorBySeverity = (colorType, isLight = true) => {
    const colorMap = {
        'critical': cssVar('--red-critical'),
        'error': cssVar('--red-error'),
        'warning': cssVar('--yellow-warning'),
        'info': cssVar('--blue-info'),
        'debug': cssVar('--grey-debug'),
        'success': cssVar('--green-success'),
        'default': cssVar('--grey-debug')
    };

    return colorMap[colorType?.toLowerCase()] || colorMap['default'];
};

const getComponents = (themeMode, selectedColorPalette) => {
    const isLight = themeMode === Theme.LIGHT;

    const headerBgColor = selectedColorPalette.medium;
    const selectedItemBgColor = isLight ? selectedColorPalette.light : selectedColorPalette.dark;
    const selectedItemHoverBgColor = isLight ? selectedColorPalette.medium : selectedColorPalette.medium;
    const pinClockColor = isLight ? selectedColorPalette.dark : selectedColorPalette.medium;

    return {
        MuiTooltip: {
            styleOverrides: {
                tooltip: {
                    fontSize: '1em',
                    maxWidth: '600px !important',
                    maxHeight: "400px !important",
                    overflow: 'auto',
                    background: isLight ? cssVar('--light-bg-secondary') : cssVar('--dark-bg-primary'),
                    color: isLight ? cssVar('--light-text-primary') : cssVar('--dark-text-primary'),
                    border: `1px solid ${isLight ? cssVar('--light-border-light') : cssVar('--dark-border-light')}`
                },
            }
        },
        MuiTextField: {
            styleOverrides: {
                root: {
                    '& .MuiOutlinedInput-root': {
                        '& fieldset': {
                            borderColor: cssVar('--light-border-input'),
                        },
                        '&:hover fieldset': {
                            borderColor: isLight ? cssVar('--light-border-hover') : cssVar('--dark-border-hover'),
                        },
                        '&.Mui-focused fieldset': {
                            borderColor: cssVar(selectedColorPalette.dark),
                        },
                        '&.Mui-disabled fieldset': {
                            borderColor: cssVar('--light-border-input'),
                            background: isLight ? cssVar('--light-disabled-overlay') : cssVar('--dark-disabled-overlay'),
                        },
                        '& .MuiInputBase-input': {
                            color: isLight ? cssVar('--light-text-primary') + ' !important' : cssVar('--dark-text-primary'),
                        },
                    }
                },
            },
        },
        MuiSelect: {
            styleOverrides: {
                root: {
                    '& fieldset': {
                        borderColor: cssVar('--light-border-input'),
                    },
                    '&:hover fieldset': {
                        borderColor: isLight ? cssVar('--light-border-hover') : cssVar('--dark-border-hover'),
                    },
                    '&.Mui-focused fieldset': {
                        borderColor: cssVar(selectedColorPalette.dark),
                    },
                    '&.Mui-disabled fieldset': {
                        borderColor: cssVar('--light-border-input'),
                        background: isLight ? cssVar('--light-disabled-overlay') : cssVar('--dark-disabled-overlay'),
                    },
                    '& .MuiSelect-select.MuiInputBase-input.MuiOutlinedInput-input': {
                        color: isLight ? cssVar('--light-text-primary') + ' !important' : cssVar('--dark-text-primary') + ' !important',
                    },
                }
            },
        },
        MuiTableHead: {
            styleOverrides: {
                root: {
                    background: cssVar(headerBgColor),
                    '& .MuiTableCell-root': {
                        color: cssVar('--table-header-text'),
                    },
                },
            },
        },
        MuiListItem: {
            styleOverrides: {
                root: {
                    '&.Mui-selected': {
                        backgroundColor: cssVar(selectedItemBgColor),
                        // '&:hover': {
                        //     backgroundColor: cssVar(selectedItemHoverBgColor),
                        // }
                    },
                },
            },
        },
        MuiPickersDay: {
            styleOverrides: {
                root: {
                    '&.Mui-selected': {
                        background: cssVar(pinClockColor),
                        '&:hover': {
                            backgroundColor: cssVar(pinClockColor)
                        }
                    }
                }
            }
        },
        MuiClock: {
            styleOverrides: {
                pin: {
                    background: cssVar(pinClockColor)
                }
            }
        },
        MuiClockPointer: {
            styleOverrides: {
                root: {
                    background: cssVar(pinClockColor)
                },
                thumb: {
                    borderColor: cssVar(pinClockColor)
                }
            }
        },
        MuiClockNumber: {
            styleOverrides: {
                root: {
                    '&.Mui-selected': {
                        background: cssVar(pinClockColor),
                        color: isLight ? '#fff' : '#000',
                        '&:hover': {
                            backgroundColor: cssVar(pinClockColor)
                        }
                    }
                }
            }
        },
        MuiTab: {
            styleOverrides: {
                root: {
                    '&.Mui-selected': {
                        color: cssVar(isLight ? selectedColorPalette.dark : selectedColorPalette.light),
                        fontWeight: 'bold',
                    }
                }
            }
        },
        MuiLinearProgress: {
            styleOverrides: {
                root: {
                    backgroundColor: isLight ? cssVar('--progress-bg-light') : cssVar('--progress-bg-dark'),
                    '& .MuiLinearProgress-bar': {
                        backgroundColor: cssVar(selectedColorPalette.light),
                    }
                },
            },
        },
        MuiTableCell: {
            styleOverrides: {
                root: {
                    '&.MuiTableCell-head': {
                        color: cssVar('--table-header-text'),
                    },
                },
            },
        },
        MuiButton: {
            styleOverrides: {
                root: {
                    color: '#fff !important'
                }
            }
        },
        MuiToolbar: {
            styleOverrides: {
                root: {
                    color: isLight ? cssVar('--light-text-primary') : cssVar('--dark-text-primary'),
                    '&.MuiTablePagination-toolbar': {
                        color: isLight ? cssVar('--light-text-primary') : cssVar('--dark-text-primary'),
                        '& *': {
                            color: isLight ? cssVar('--light-text-primary') : cssVar('--dark-text-primary'),
                        },
                        '& .MuiIconButton-root': {
                            color: isLight ? cssVar('--light-text-primary') : cssVar('--dark-text-primary'),
                            '&:hover': {
                                backgroundColor: isLight ? cssVar('--light-hover-overlay') : cssVar('--dark-hover-overlay'),
                            },
                            '&.Mui-disabled': {
                                color: isLight ? cssVar('--light-text-disabled') : cssVar('--dark-text-disabled'),
                            },
                        },
                    },
                },
            },
        },
        MuiTablePagination: {
            styleOverrides: {
                root: {
                    color: isLight ? cssVar('--light-text-primary') : cssVar('--dark-text-primary'),
                },
                toolbar: {
                    color: isLight ? cssVar('--light-text-primary') : cssVar('--dark-text-primary'),
                },
                actions: {
                    color: isLight ? cssVar('--light-text-primary') : cssVar('--dark-text-primary'),
                    '& .MuiIconButton-root': {
                        color: isLight ? cssVar('--light-text-primary') : cssVar('--dark-text-primary'),
                        '&:hover': {
                            backgroundColor: isLight ? cssVar('--light-hover-overlay') : cssVar('--dark-hover-overlay'),
                        },
                        '&.Mui-disabled': {
                            color: isLight ? cssVar('--light-text-disabled') : cssVar('--dark-text-disabled'),
                        },
                    },
                },
                selectIcon: {
                    color: isLight ? cssVar('--light-text-primary') : cssVar('--dark-text-primary'),
                },
                displayedRows: {
                    color: isLight ? cssVar('--light-text-primary') : cssVar('--dark-text-primary'),
                },
                selectLabel: {
                    color: isLight ? cssVar('--light-text-primary') : cssVar('--dark-text-primary'),
                },
            },
        },
    };
};

export const getTheme = (themeMode = Theme.LIGHT, baseColorName = DEFAULT_BASE_COLOR) => {
    const selectedPalette = baseColorPalettes[baseColorName] || baseColorPalettes[DEFAULT_BASE_COLOR];

    if (themeMode === Theme.DARK) {
        return createTheme({
            typography: typography,
            components: getComponents(Theme.DARK, selectedPalette),
            palette: {
                mode: Theme.DARK,
                primary: {
                    main: cssVar(selectedPalette.medium),
                    light: cssVar(selectedPalette.light),
                    dark: cssVar(selectedPalette.dark)
                },
                secondary: {
                    main: cssVar('--dark-bg-secondary'),
                    light: cssVar('--dark-border-default'),
                    dark: cssVar('--dark-bg-primary')
                },
                error: {
                    main: cssVar('--red-error'),
                },
                warning: {
                    main: cssVar('--yellow-warning'),
                },
                info: {
                    main: cssVar('--blue-info'),
                },
                success: {
                    main: cssVar('--green-success'),
                },
                white: {
                    main: 'white'
                },
                text: {
                    primary: cssVar('--dark-text-primary'),
                    secondary: cssVar('--dark-text-secondary'),
                    tertiary: cssVar('--yellow-warning'),
                    quaternary: cssVar('--yellow-warning'),
                    critical: cssVar('--red-critical'),
                    error: cssVar('--red-error'),
                    warning: cssVar('--yellow-warning'),
                    info: cssVar('--blue-info'),
                    success: cssVar('--green-success'),
                    debug: cssVar('--grey-debug'),
                    default: cssVar('--dark-text-primary'),
                    white: '#fff',
                    black: '#000',
                    disabled: cssVar('--dark-text-disabled')
                },
                background: {
                    default: cssVar('--dark-bg-primary'),
                    primary: cssVar('--dark-bg-primary'),
                    secondary: cssVar('--dark-bg-secondary'),
                    paper: cssVar('--dark-bg-secondary'),
                    commonKey: cssVar(selectedPalette.contrasting),
                    nodeHeader: cssVar(selectedPalette.medium),
                    icon: cssVar(selectedPalette.light)
                }
            }
        });
    }

    // Light Theme
    return createTheme({
        typography: typography,
        components: getComponents(Theme.LIGHT, selectedPalette),
        palette: {
            mode: Theme.LIGHT,
            primary: {
                main: cssVar(selectedPalette.medium),
                light: cssVar(selectedPalette.light),
                dark: cssVar(selectedPalette.dark)
            },
            secondary: {
                main: cssVar('--light-border-light'),
                light: cssVar('--light-bg-secondary'),
                dark: cssVar('--light-border-default')
            },
            error: {
                main: cssVar('--red-error'),
            },
            warning: {
                main: cssVar('--yellow-warning'),
            },
            info: {
                main: cssVar('--blue-info'),
            },
            success: {
                main: cssVar('--green-success'),
            },
            white: {
                main: 'white'
            },
            text: {
                primary: cssVar('--light-text-primary'),
                secondary: cssVar('--light-text-secondary'),
                tertiary: cssVar('--yellow-warning'),
                quaternary: cssVar('--yellow-warning'),
                critical: cssVar('--red-critical'),
                error: cssVar('--red-error'),
                warning: cssVar('--yellow-warning'),
                info: cssVar('--blue-info'),
                success: cssVar('--green-success'),
                debug: cssVar('--grey-debug'),
                default: cssVar('--light-text-primary'),
                white: '#fff',
                black: '#000',
                disabled: cssVar('--light-text-disabled')
            },
            background: {
                default: cssVar(selectedPalette.light),
                primary: cssVar('--light-bg-primary'),
                paper: cssVar('--light-bg-secondary'),
                secondary: cssVar(selectedPalette.light),
                commonKey: cssVar(selectedPalette.contrasting),
                nodeHeader: cssVar(selectedPalette.dark),
                icon: cssVar(selectedPalette.medium)
            }
        }
    });
};

