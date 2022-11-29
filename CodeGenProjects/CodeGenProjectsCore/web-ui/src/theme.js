import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
    typography: {
        "fontFamily": `"Roboto", "Helvetica", "Arial", sans-serif`,
        "fontSize": 10,
        "fontWeightLight": 300,
        "fontWeightRegular": 500,
        "fontWeightMedium": 500
    },
    palette: {
        background: {
            default: "white"
        }
    },
    components: {
        MuiTooltip: {
            styleOverrides: {
                tooltip: {
                    fontSize: '0.9em'
                }
            }
        }
    }
});