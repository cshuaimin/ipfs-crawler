import Vue from 'vue'
import Router from 'vue-router'
import Search from '@/components/Search'
import Results from '@/components/Results'

Vue.use(Router)

export default new Router({
  routes: [
    {
      path: '/',
      name: 'Search',
      component: Search
    },
    {
      path: '/search/:query',
      name: 'Results',
      component: Results,
      props: true
    }
  ]
})
