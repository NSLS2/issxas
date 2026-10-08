from lmfit import Model
from scipy import interpolate
import numpy as np

def gaussian(x, amp, cen, sigma, bkg):
    """1-d gaussian: gaussian(x, amp, cen, sigma, bkg)"""
    return (bkg + amp * np.exp(-(x-cen)**2 / (2*sigma**2)))



def get_normalized_gaussian_scan(db, uid, return_norm_param=False):
    t = db[uid].table()
    E = t['hhm_energy'].values
    I = t['pil100k2_stats1_total'].values
#     I_smooth = hampel(I)
#     I_smooth = I
    offset = np.mean(np.hstack((I[:2], I[-2:])))
    I -= offset
    scale = I.max()
    I /= scale
    if return_norm_param:
        return E, np.array(I), scale, offset
    return E, np.array(I)


def estimate_center_and_width_of_peak(E, I):
    E_cen = E[np.argmax(np.abs(I))]
    x = np.abs(I - 0.5)
    e_low = E < E_cen
    e_high = E > E_cen
    x1 = E[e_low][np.argmin(x[e_low])]
    x2 = E[e_high][np.argmin(x[e_high])]
    fwhm = np.abs(x1 - x2)
    return E_cen, fwhm


def estimate_center_and_width_of_peak_update(E, I):
    # updated to not require normalized spectrum
    I_norm = (I - I.min()) / (I.max() - I.min())
    E_grid = np.linspace(E.min(), E.max(), E.size * 10)
    I_grid_norm = np.interp(E_grid, E[np.argsort(E)], I_norm[np.argsort(E)])
    return estimate_center_and_width_of_peak(E_grid, I_grid_norm)
    # E_cen = E[np.argmax(np.abs(I))]
    # x = np.abs(I - 0.5*(I.max() - I.min()))
    # e_low = E < E_cen
    # e_high = E > E_cen
    # x1 = E[e_low][np.argmin(x[e_low])]
    # x2 = E[e_high][np.argmin(x[e_high])]
    # fwhm = np.abs(x1 - x2)
    return E_cen, fwhm



def fit_gaussian(E, I, Ecen0, fwhm0, amp=1, bkg=0):
    gmodel = Model(gaussian)
    result = gmodel.fit(I, x=E, amp=amp, cen=Ecen0, sigma=fwhm0/2.355, bkg=bkg)
    Ecen = result.params['cen'].value 
    fwhm = np.abs(result.params['sigma'].value * 2.355)
    I_fit = (result.best_fit - result.params['bkg'].value) / result.params['amp']
    I_cor = (I - result.params['bkg'].value) / result.params['amp']
    I_fit_raw = result.best_fit
    return Ecen, fwhm, I_cor, I_fit, I_fit_raw

def fit_gaussian_with_estimation(E, I):
    Ecen0, fwhm0 = estimate_center_and_width_of_peak_update(E, I)
    # print(Ecen0, fwhm0)
    return fit_gaussian(E, I, Ecen0, fwhm0, amp=np.ptp(I), bkg=I.min())


def fit_linear_surf(x, y, z, plotting=False):
    A = np.hstack((x[:, None], y[:, None], np.ones((x.size, 1))))
    c, _, _, _ = np.linalg.lstsq(A, z, rcond=-1)
    # if plotting:
    #     try:
    #         mplot3d
    #     except NameError:
    #         from mpl_toolkits import mplot3d
    #     fig = plt.figure()
    #     ax = plt.axes(projection='3d')
    #     ax.scatter3D(x, y, z, marker='.', color='k')
    #     ax.scatter3D(x, y, A @ c, marker='.', color='r')
    return c

class Nominal2ActualConverter:

    def __init__(self, x_nominal, x_actual, n_poly=2):
        self.p_n2a = np.polyfit(x_nominal, x_actual, n_poly)
        self.p_a2n = np.polyfit(x_actual, x_nominal, n_poly)
        self.x_nominal = x_nominal
        self.x_actual = x_actual
        self.n_poly = n_poly

    def nom2act(self, e_nom):
        return np.polyval(self.p_n2a, e_nom)

    def act2nom(self, e_act):
        return np.polyval(self.p_a2n, e_act)

class Nominal2ActualConverterWithLinearInterpolation:

    def __init__(self):
        self.x_nom = []
        self.x_act = []

    def append_point(self, x_nom, x_act):
        if np.any(np.isclose(x_nom, self.x_nom, atol=1e-4)) or np.any(np.isclose(x_act, self.x_act, atol=1e-4)):
            return
        self.x_nom.append(x_nom)
        self.x_act.append(x_act)

    @property
    def npt(self):
        return len(self.x_nom)

    def nom2act(self, x_nom):
        if self.npt == 0:
            return x_nom
        elif self.npt == 1:
            return x_nom - (self.x_nom[0] - self.x_act[0])
        else:
            f = interpolate.interp1d(self.x_nom, self.x_act, kind='linear', fill_value='extrapolate')
            return f(x_nom)

    def act2nom(self, x_act):
        if self.npt == 0:
            return x_act
        elif self.npt == 1:
            return x_act - (self.x_act[0] - self.x_nom[0])
        else:
            f = interpolate.interp1d(self.x_act, self.x_nom, kind='linear', fill_value='extrapolate')
            return f(x_act)

