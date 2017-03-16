import numpy as np
from scipy import optimize
from pyftp.template import Template


class SlowTemplatePeriodogram(object):
    """Slow periodogram built from a template model.

    When computing the periodogram, this performs a nonlinear optimization at
    each frequency. This is used mainly for testing the faster method
    available in FastTemplatePeriodogram

    Parameters
    ----------
    t : array_like
        sequence of observation times
    y : array_like
        sequence of observations associated with times t
    dy : float, array_like (optional)
        error or sequence of observational errors associated with times t
    template : Template object
        callable object that returns the template value as a function of phase
    """
    def __init__(self, t, y, dy=None, template=None):
        self.t, self.y, self.dy = self._validate_inputs(t, y, dy)
        self.template = template

    def _validate_inputs(self, t, y, dy):
        if dy is None:
            # TODO: handle dy = None case more efficiently
            t, y, dy = np.broadcast_arrays(t, y, 1.0)
        else:
            t, y, dy = np.broadcast_arrays(t, y, dy)
        if t.ndim != 1:
            raise ValueError("Inputs (t, y, dy) must be 1-dimensional")
        return t, y, dy

    def _chi2_ref(self):
        """Compute the reference chi-square"""
        weights = self.dy ** -2
        weights /= weights.sum()
        ymean = np.dot(weights, self.y)
        return np.sum((self.y - ymean) ** 2 / self.dy ** 2)

    def _minimize_chi2_at_single_freq(self, freq):
        t_phase = (self.t * freq) % 1
        def chi2(params):
            phase, offset, amp = params
            y_model = offset + amp * self.template(self.t * freq - phase)
            return np.sum((y_model - self.y) ** 2 / self.dy ** 2)
        params0 = [0, np.mean(self.y), np.std(self.y)]
        return optimize.minimize(chi2, params0, method='l-bfgs-b')

    def power(self, freq):
        """Compute a template-based periodogram at the given frequencies

        Parameters
        ----------
        freq : array_like
            frequencies at which to evaluate the template periodogram

        Returns
        -------
        power : np.ndarray
            normalized power spectrum computed at the given frequencies
        """
        freq = np.asarray(freq)
        results = list(map(self._minimize_chi2_at_single_freq, freq.flat))
        failures = sum([not res.success for res in results])
        if failures:
            warnings.warn("{0}/{1} frequency values failed to "
                          "converge".format(failures, len(freq)))
        chi2 = np.array([res.fun for res in results])
        return np.reshape(1 - chi2 / self._chi2_ref(), freq.shape)