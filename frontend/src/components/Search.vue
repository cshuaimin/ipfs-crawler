<template>
  <div class="container">
    <img class="ipfs-logo" src="../assets/ipfs.svg" alt="IPFS">
    <Input
        title="Search IPFS"
        :autofocus="true"
        icon="android-search"
        placeholder="Search IPFS..."
        size="large"
        @on-enter="search"
        @on-click="search"
        v-model="query"
        >
    </Input>
  </div>
</template>

<style scoped>
.container {
  width: 600px;
  margin: 0 auto;
}

.ipfs-logo {
  width: 256px;
  display: block;
  margin: 18vh auto 20px auto;
}
</style>

<script>
export default {
  name: 'Search',
  data () {
    return {
      query: ''
    }
  },
  methods: {
    search () {
      this.$router.push(`/search/${this.query}`)
    }
  }
}
</script>
