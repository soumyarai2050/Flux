import { createTheme } from '@mui/material/styles';

export const Theme = {
    LIGHT: 'light',
    DARK: 'dark'
}

export function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

const typography = {
    "fontFamily": `"Roboto", "Helvetica", "Arial", sans-serif`,
    "fontSize": 11,
    "fontWeightLight": 300,
    "fontWeightRegular": 500,
    "fontWeightMedium": 500
}

const lightThemeComponents = {
    MuiTooltip: {
        styleOverrides: {
            tooltip: {
                fontSize: '1em',
                maxWidth: '600px !important',
                maxHeight: "400px !important",
                overflow: 'auto',
                background: cssVar('--light-primary-main'),
                color: '#121212',
                border: `1px solid ${cssVar('--light-primary-dark')}`
            },
        }
    },
    MuiTextField: {
        styleOverrides: {
            root: {
                '& .MuiOutlinedInput-root': {
                    '& fieldset': {
                        borderColor: cssVar('--grey-400'),
                    },
                    '&:hover fieldset': {
                        borderColor: cssVar('--grey-dark'),
                    },
                    '&.Mui-focused fieldset': {
                        borderColor: cssVar('--blue-600'),
                    },
                    '&.Mui-disabled fieldset': {
                        borderColor: cssVar('--grey-400'),
                        background: 'rgba(0, 0, 0, 0.1)',
                    },
                }
            },
        },
    },
    MuiSelect: {
        styleOverrides: {
            root: {
                '&.Mui-disabled fieldset': {
                    borderColor: cssVar('--grey-400'),
                    background: 'rgba(0, 0, 0, 0.1)',
                },
            }
        },
    },
    MuiTableHead: {
        styleOverrides: {
            root: {
                // '& .MuiTableCell-root': {
                //     color: 'white !important',
                // },
                background: cssVar('--teal-400')
            },
        },
    },
    MuiTableRow: {
        styleOverrides: {
            root: {
                '&:nth-of-type(even)': {
                    // backgroundColor: cssVar('--grey-100'),
                    // opacity: 0.85
                },
                '&.Mui-selected': {
                    backgroundColor: cssVar('--blue-100'),
                    '&:hover': {
                        backgroundColor: cssVar('--blue-200'),
                    }
                },
            },
        },
    },
    MuiListItem: {
        styleOverrides: {
            root: {
                '&.Mui-selected': {
                    backgroundColor: cssVar('--blue-100'),
                    '&:hover': {
                        backgroundColor: cssVar('--blue-200'),
                    }
                },
            },
        },
    },
}

const darkThemeComponents = {
    MuiTooltip: {
        styleOverrides: {
            tooltip: {
                fontSize: '1em',
                maxWidth: '600px !important',
                maxHeight: "400px !important",
                overflow: 'auto',
                background: cssVar('--dark-primary-main'),
                border: `1px solid ${cssVar('--dark-primary-dark')}`
            },
        }
    },
    MuiTextField: {
        styleOverrides: {
            root: {
                '& .MuiOutlinedInput-root': {
                    '& fieldset': {
                        borderColor: cssVar('--grey-400'),
                    },
                    '&:hover fieldset': {
                        borderColor: cssVar('--grey-light'),
                    },
                    '&.Mui-focused fieldset': {
                        borderColor: cssVar('--blue-600'),
                    },
                    '&.Mui-disabled fieldset': {
                        borderColor: cssVar('--grey-400'),
                        background: 'rgba(255, 255, 255, 0.1)',
                    },
                }
            },
        },
    },
    MuiSelect: {
        styleOverrides: {
            root: {
                '& fieldset': {
                    borderColor: cssVar('--grey-400'),
                },
                '&.Mui-disabled fieldset': {
                    borderColor: cssVar('--grey-400'),
                    background: 'rgba(255, 255, 255, 0.1)',
                },
            }
        },
    },
    MuiTableHead: {
        styleOverrides: {
            root: {
                // '& .MuiTableCell-root': {
                //     color: 'white !important',
                // },
                background: cssVar('--blue-accent-400')
            },
        },
    },
    MuiTableRow: {
        styleOverrides: {
            root: {
                '&:nth-of-type(even)': {
                    // backgroundColor: cssVar('--grey-800'),
                    // opacity: 0.85
                },
                '&.Mui-selected': {
                    backgroundColor: cssVar('--indigo-300'),
                    '&:hover': {
                        backgroundColor: cssVar('--indigo-400'),
                    }
                },
            },
        },
    },
    MuiListItem: {
        styleOverrides: {
            root: {
                '&.Mui-selected': {
                    backgroundColor: cssVar('--indigo-300'),
                    '&:hover': {
                        backgroundColor: cssVar('--indigo-400'),
                    }
                },
            },
        },
    },
    MuiLinearProgress: {
        styleOverrides: {
            root: {
                backgroundColor: cssVar('--grey-800'),
            },
        },
    },
}

export const lightTheme = createTheme({
    typography: typography,
    components: lightThemeComponents,
    palette: {
        mode: Theme.LIGHT,
        primary: {
            main: cssVar('--light-primary-main'),
            light: cssVar('--light-primary-light'),
            dark: cssVar('--light-primary-dark')
        },
        secondary: {
            main: cssVar('--light-primary-main'),
            light: cssVar('--light-primary-light'),
            dark: cssVar('--light-primary-dark')
        },
        text: {
            primary: '#010101',
            secondary: '#121212',
            tertiary: cssVar('--yellow-400'),
            quaternary: cssVar('--yellow-100'),
            critical: cssVar('--red-800'),
            error: cssVar('--red-600'),
            warning: cssVar('--yellow-800'),
            info: cssVar('--blue-400'),
            success: cssVar('--green-400'),
            debug: cssVar('grey-600'),
            default: '#010101',
            white: '#fff',
            disabled: cssVar('--grey-600')
        },
        background: {
            default: cssVar('--light-primary-dark'),
            primary: cssVar('--light-primary-dark'),
            secondary: cssVar('--teal-400'),
            commonKey: cssVar('--teal-400'),
            nodeHeader: cssVar('--teal-400'),
            icon: cssVar('--teal-400')
        }
    }
})

export const darkTheme = createTheme({
    typography: typography,
    components: darkThemeComponents,
    palette: {
        mode: Theme.DARK,
        primary: {
            main: cssVar('--dark-primary-main'),
            light: cssVar('--dark-primary-light'),
            dark: cssVar('--dark-primary-dark')
        },
        secondary: {
            main: cssVar('--dark-secondary-main'),
            light: cssVar('--dark-secondary-light'),
            dark: cssVar('--dark-secondary-dark')
        },
        text: {
            primary: '#fff',
            tertiary: cssVar('--yellow-400'),
            quaternary: cssVar('--yellow-100'),
            critical: cssVar('--red-800'),
            error: cssVar('--red-600'),
            warning: cssVar('--yellow-800'),
            info: cssVar('--blue-400'),
            success: cssVar('--green-400'),
            debug: cssVar('grey-600'),
            default: '#fff',
            white: '#fff'
        },
        background: {
            primary: cssVar('--dark-primary-main'),
            secondary: cssVar('--dark-primary-light'),
            commonKey: cssVar('--dark-primary-light'),
            nodeHeader: cssVar('--blue-accent-400'),
            icon: cssVar('--blue-accent-400')
        }
    }
})

export const getTheme = (theme) => {
    return theme === Theme.DARK ? darkTheme : lightTheme;
}