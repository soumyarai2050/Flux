import React, { useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import _, { cloneDeep } from 'lodash';
import { makeStyles } from '@mui/styles';
import {
    getAllUILayout, getUILayout, createUILayout, updateUILayout,
    resetUILayout, setModifiedUILayout, setSelectedUILayoutId, resetSelectedUILayoutId, resetError
} from '../features/uiLayoutSlice';
import { getLayout } from '../projectSpecificUtils';
import { Responsive, WidthProvider } from "react-grid-layout";
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import { Paper, Box } from '@mui/material';
import { Widgets } from '@mui/icons-material';
import PairStratParams from '../widgets/PairStratParams';
import StratStatus from '../widgets/StratStatus';
import StratLimits from '../widgets/StratLimits';
import OrderLimits from '../widgets/OrderLimits';
import PortfolioLimits from '../widgets/PortfolioLimits';
import PortfolioStatus from '../widgets/PortfolioStatus';
import StratCollection from '../widgets/StratCollection';
import SideDrawer from './SideDrawer';
import ToggleIcon from '../components/ToggleIcon';
import { DB_ID, COOKIE_NAME } from '../constants';
import { Dialog, DialogContent, DialogActions, DialogContentText, TextField, Button, DialogTitle, Autocomplete } from '@mui/material';
import Icon from './Icon';
import { DashboardCustomize, SaveAs } from '@mui/icons-material';
import Cookie from 'universal-cookie';

const ResponsiveGridLayout = WidthProvider(Responsive);

const useStyles = makeStyles({
    layout: {
        display: 'flex'
    },
    grid: {
        flex: 1,
        overflow: 'auto'
    },
    widget: {
        background: 'whitesmoke !important',
    },
    icon: {
        color: 'inherit !important',
    },
    iconButton: {
        backgroundColor: '#ccc !important',
        margin: '5px !important',
        '&:hover': {
            backgroundColor: '#ddd !important'
        }
    },
    dialogContentText: {
        margin: '10px 0 !important'
    }
})

const Layout = (props) => {
    const { uiLayoutArray, uiLayout, modifiedUILayout, selectedUILayoutId, loading, error } = useSelector(state => state.uiLayout);
    const [layouts, setLayouts] = useState(getLayout());
    const [draggable, setDraggable] = useState(false);
    const [openSaveLayout, setOpenSaveLayout] = useState(false);
    const [openLoadLayout, setOpenLoadLayout] = useState(false);
    const [searchValue, setSearchValue] = useState('');
    const [profileId, setProfileId] = useState('');
    const [show, setShow] = useState({
        pair_strat_params: true,
        strat_status: true,
        strat_limits: true,
        order_limits: true,
        portfolio_limits: true,
        portfolio_status: true,
        strat_collection: true
    });

    const classes = useStyles();
    const dispatch = useDispatch();

    const defaultProps = {
        layouts: {
            lg: getLayout()
        },
        breakpoints: { lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 },
        cols: { lg: 18, md: 12, sm: 6, xs: 4, xxs: 2 },
        className: 'layout',
        rowHeight: 50,
        margin: { lg: [8, 8], md: [5, 5] },
        preventCollision: true,
        allowOverlap: false,
        autoSize: false,
        isBounded: false,
        compactType: null,
        useCSSTransforms: true,
        resizeHandles: ['ne', 'se']
    }

    useEffect(() => {
        dispatch(getAllUILayout());
    }, [])

    useEffect(() => {
        let cookie = new Cookie();
        cookie = cookie.get(COOKIE_NAME);
        if (cookie) {
            dispatch(getUILayout(cookie));
        }
    }, [])

    useEffect(() => {
        if (uiLayout.widget_ui_data) {
            setLayouts(uiLayout.widget_ui_data);
            setProfileId(uiLayout.profile_id);
        }
    }, [uiLayout])

    const onToggleDrag = () => {
        setDraggable(!draggable);
    }

    const onSave = () => {
        if (uiLayoutArray.filter(l => l.profile_id === profileId).length > 0) {
            let layout = uiLayoutArray.filter(l => l.profile_id === profileId)[0];
            layout = cloneDeep(layout);
            layout.widget_ui_data = layouts;
            dispatch(updateUILayout(layout));
        } else {
            let layout = { profile_id: profileId, widget_ui_data: layouts }
            dispatch(createUILayout(layout));
        }
        setOpenSaveLayout(false);
        setProfileId(uiLayout.profile_id ? uiLayout.profile_id : '');
    }

    const onLoad = () => {
        setLayouts(searchValue.widget_ui_data);
        setOpenLoadLayout(false);
        setSearchValue('');
        let cookie = new Cookie();
        cookie.set(COOKIE_NAME, searchValue[DB_ID], { path: '/', maxAge: 2592000 })
    }

    const onToggleWidget = (name) => {
        setShow({ ...show, [name]: !show[name] });
        setLayouts(uiLayout.widget_ui_data ? uiLayout.widget_ui_data : getLayout());
    }

    const onLayoutChange = (layout) => {
        setLayouts(layout);
    }

    const onSearchValueChange = (e, value) => {
        setSearchValue(value);
    }

    const onProfileIdChange = (e) => {
        setProfileId(e.target.value);
    }

    const onCloseSaveLayout = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        setOpenSaveLayout(false);
        setProfileId(uiLayout.profile_id ? uiLayout.profile_id : '');
    }

    const onCloseLoadLayout = (e, reason) => {
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') return;
        setOpenLoadLayout(false);
        setSearchValue('');
    }

    const getLayoutById = (id) => {
        let layout = layouts.filter(layout => layout.i === id)[0];
        return layout ? layout : { i: id, x: 0, y: 0, w: 4, h: 4 };
    }

    return (
        <Box className={classes.layout}>
            <SideDrawer draggable={draggable} onToggleDrag={onToggleDrag}>
                <Icon className={classes.iconButton} title='Load Layout' onClick={() => setOpenLoadLayout(true)}>
                    <DashboardCustomize fontSize='medium' />
                </Icon>
                <Icon className={classes.iconButton} title='Save Layout' onClick={() => setOpenSaveLayout(true)}>
                    <SaveAs fontSize='medium' />
                </Icon>
                <ToggleIcon title='Pair Strat Params' name='pair_strat_params' selected={show.pair_strat_params} onClick={onToggleWidget}>
                    <Widgets className={classes.icon} fontSize='large' />
                </ToggleIcon>
                <ToggleIcon title='Strat Status' name='strat_status' selected={show.strat_status} onClick={onToggleWidget}>
                    <Widgets className={classes.icon} fontSize='large' />
                </ToggleIcon>
                <ToggleIcon title='Strat Limits' name='strat_limits' selected={show.strat_limits} onClick={onToggleWidget}>
                    <Widgets className={classes.icon} fontSize='large' />
                </ToggleIcon>
                <ToggleIcon title='Order Limits' name='order_limits' selected={show.order_limits} onClick={onToggleWidget}>
                    <Widgets className={classes.icon} fontSize='large' />
                </ToggleIcon>
                <ToggleIcon title='Portfolio Limits' name='portfolio_limits' selected={show.portfolio_limits} onClick={onToggleWidget}>
                    <Widgets className={classes.icon} fontSize='large' />
                </ToggleIcon>
                <ToggleIcon title='Portfolio Status' name='portfolio_status' selected={show.portfolio_status} onClick={onToggleWidget}>
                    <Widgets className={classes.icon} fontSize='large' />
                </ToggleIcon>
                <ToggleIcon title='Strat Collection' name='strat_collection' selected={show.strat_collection} onClick={onToggleWidget}>
                    <Widgets className={classes.icon} fontSize='large' />
                </ToggleIcon>
            </SideDrawer>
            <ResponsiveGridLayout
                {...defaultProps}
                layouts={{ lg: layouts }}
                className={classes.grid}
                isDraggable={draggable}
                isResizable={draggable}
                onLayoutChange={onLayoutChange}>

                {show.pair_strat_params &&
                    <Paper key='pair_strat_params' className={classes.widget} data-grid={getLayoutById('pair_strat_params')}>
                        <PairStratParams name="pair_strat_params"
                        />
                   </Paper>
                }
                {show.strat_status &&
                    <Paper key='strat_status' className={classes.widget} data-grid={getLayoutById('strat_status')}>
                        <StratStatus name="strat_status"
                        />
                   </Paper>
                }
                {show.strat_limits &&
                    <Paper key='strat_limits' className={classes.widget} data-grid={getLayoutById('strat_limits')}>
                        <StratLimits name="strat_limits"
                        />
                   </Paper>
                }
                {show.order_limits &&
                    <Paper key='order_limits' className={classes.widget} data-grid={getLayoutById('order_limits')}>
                        <OrderLimits name="order_limits"
                        />
                   </Paper>
                }
                {show.portfolio_limits &&
                    <Paper key='portfolio_limits' className={classes.widget} data-grid={getLayoutById('portfolio_limits')}>
                        <PortfolioLimits name="portfolio_limits"
                        />
                   </Paper>
                }
                {show.portfolio_status &&
                    <Paper key='portfolio_status' className={classes.widget} data-grid={getLayoutById('portfolio_status')}>
                        <PortfolioStatus name="portfolio_status"
                        />
                   </Paper>
                }
                {show.strat_collection &&
                    <Paper key='strat_collection' className={classes.widget} data-grid={getLayoutById('strat_collection')}>
                        <StratCollection name="strat_collection"
                        />
                   </Paper>
                }
            </ResponsiveGridLayout>
            <Dialog
                open={openSaveLayout}
                onClose={onCloseSaveLayout}>
                <DialogTitle>Save Layout</DialogTitle>
                <DialogContent>
                    <DialogContentText className={classes.dialogContentText}>
                        To save the layout, please enter profile id. If profile id already exists, layout will be overwritten.
                    </DialogContentText>
                    <TextField
                        label="Profile Id"
                        variant="standard"
                        error={uiLayoutArray.filter(layout => layout.profile_id === profileId).length > 0}
                        helperText={uiLayoutArray.filter(layout => layout.profile_id === profileId).length > 0 ? 'Profile Id already exists. Click on Save to overwrite.' : ''}
                        value={profileId}
                        onChange={onProfileIdChange}
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={onCloseSaveLayout} autoFocus>Discard</Button>
                    <Button onClick={onSave} autoFocus>Save</Button>
                </DialogActions>
            </Dialog>
            <Dialog
                open={openLoadLayout}
                onClose={onCloseLoadLayout}>
                <DialogTitle>Load Layout</DialogTitle>
                <DialogContent>
                    <DialogContentText className={classes.dialogContentText}>
                        To load the layout, select the profile id.
                    </DialogContentText>
                    <Autocomplete
                        options={uiLayoutArray}
                        getOptionLabel={(option) => option.profile_id ? option.profile_id : ''}
                        disableClearable
                        variant='outlined'
                        size='small'
                        value={searchValue}
                        onChange={onSearchValueChange}
                        renderInput={(params) => <TextField {...params} label="Profile id" />}
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={onCloseLoadLayout} autoFocus>Discard</Button>
                    <Button disabled={searchValue ? false : true} onClick={onLoad} autoFocus>Load</Button>
                </DialogActions>
            </Dialog>
        </Box>
    )
}

export default Layout;